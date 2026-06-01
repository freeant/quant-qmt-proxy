from __future__ import annotations

import json
import threading
import time
from typing import Any, Protocol

from app.config import RedisConfig, Settings, XTQuantMode
from app.utils.logger import logger


class SubscriptionLike(Protocol):
    subscription_id: str
    subscription_type: str
    persistent: bool

try:
    import redis
except ImportError:
    redis = None


class RedisStreamSink:
    def __init__(self, settings: Settings, client: Any | None = None):
        self.settings = settings
        self.config: RedisConfig = settings.redis
        self._client = client
        self._lock = threading.Lock()
        self._publish_total = 0
        self._publish_errors = 0
        self._publish_skipped_circuit = 0
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0
        self._last_publish_latency_ms = 0.0

    @property
    def enabled(self) -> bool:
        return bool(self.config.enabled)

    def build_stream_key(self, subscription_id: str, subscription_type: str) -> str:
        prefix = self.config.stream_prefix
        if subscription_type == "whole_quote":
            return f"{prefix}:whole:{subscription_id}"
        return f"{prefix}:quote:{subscription_id}"

    def should_mirror(self, record: SubscriptionLike) -> bool:
        if not self.enabled:
            return False
        if record.subscription_type == "whole_quote":
            if not self.settings.xtquant.data.whole_quote_enabled:
                return False
            if not self.config.mirror_whole_quote:
                return False
        if not record.persistent and not self.config.mirror_ephemeral:
            return False
        mode = self.settings.xtquant.mode
        if mode == XTQuantMode.MOCK and not self.config.mirror_mock:
            return False
        return True

    def publish(self, record: SubscriptionLike, event: dict[str, Any]) -> None:
        if not self.should_mirror(record):
            return
        self._xadd(record, event)

    def publish_subscription_ready(self, record: SubscriptionLike) -> None:
        if not self.enabled or not self.config.publish_subscription_ready:
            return
        if not self.should_mirror(record):
            return

        now_ms = int(time.time() * 1000)
        event = {
            "symbol": getattr(record, "symbols", [""])[0] if getattr(record, "symbols", None) else "",
            "period": getattr(record, "period", "tick"),
            "event_time_ms": now_ms,
            "payload_type": "subscription_ready",
            "data": {
                "subscription_id": record.subscription_id,
                "subscription_type": record.subscription_type,
                "persistent": record.persistent,
                "symbols": list(getattr(record, "symbols", []) or []),
                "markets": list(getattr(record, "markets", []) or []),
                "period": getattr(record, "period", ""),
                "redis_stream_key": self.build_stream_key(record.subscription_id, record.subscription_type),
            },
        }
        self._xadd(record, event, bypass_circuit=True)

    def on_subscription_deleted(self, record: SubscriptionLike) -> None:
        if not self.enabled:
            return
        client = self._get_client()
        if client is None:
            return

        stream_key = self.build_stream_key(record.subscription_id, record.subscription_type)
        try:
            if self.config.grace_ttl_seconds > 0:
                client.expire(stream_key, int(self.config.grace_ttl_seconds))
            elif self.config.delete_stream_on_unsubscribe:
                client.delete(stream_key)
        except Exception as exc:
            logger.warning(f"redis stream cleanup failed: stream={stream_key}, error={exc}")

    def ping(self) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            return bool(client.ping())
        except Exception as exc:
            logger.warning(f"redis ping failed: {exc}")
            return False

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "publish_total": self._publish_total,
                "publish_errors": self._publish_errors,
                "publish_skipped_circuit": self._publish_skipped_circuit,
                "consecutive_failures": self._consecutive_failures,
                "circuit_open": self._is_circuit_open_locked(),
                "last_publish_latency_ms": round(self._last_publish_latency_ms, 3),
            }

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None

    def _xadd(self, record: SubscriptionLike, event: dict[str, Any], *, bypass_circuit: bool = False) -> None:
        if not bypass_circuit and self._is_circuit_open():
            with self._lock:
                self._publish_skipped_circuit += 1
            return

        client = self._get_client()
        if client is None:
            self._record_error("redis client unavailable", bypass_circuit=bypass_circuit)
            return

        stream_key = self.build_stream_key(record.subscription_id, record.subscription_type)
        payload = self._build_envelope(record, event)
        maxlen = self._maxlen_for(record)
        started = time.perf_counter()
        try:
            client.xadd(
                stream_key,
                {"payload": payload},
                maxlen=maxlen,
                approximate=True,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            with self._lock:
                self._publish_total += 1
                self._last_publish_latency_ms = elapsed_ms
                self._consecutive_failures = 0
                self._circuit_open_until = 0.0
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            with self._lock:
                self._last_publish_latency_ms = elapsed_ms
            self._record_error(f"redis xadd failed: stream={stream_key}, error={exc}", bypass_circuit=bypass_circuit)

    def _is_circuit_open(self) -> bool:
        with self._lock:
            return self._is_circuit_open_locked()

    def _is_circuit_open_locked(self) -> bool:
        if not self.config.circuit_breaker_enabled:
            return False
        if time.monotonic() >= self._circuit_open_until:
            return False
        return True

    def _get_client(self) -> Any | None:
        if self._client is not None:
            return self._client
        if not self.enabled or redis is None:
            return None
        timeout_seconds = max(self.config.write_timeout_ms / 1000.0, 0.001)
        try:
            self._client = redis.from_url(
                self.config.url,
                decode_responses=True,
                socket_connect_timeout=self.config.connect_timeout_seconds,
                socket_timeout=timeout_seconds,
            )
            return self._client
        except Exception as exc:
            logger.warning(f"redis connect failed: {exc}")
            return None

    def _maxlen_for(self, record: SubscriptionLike) -> int:
        if record.subscription_type == "whole_quote":
            return self.config.whole_quote_maxlen
        return self.config.maxlen

    def _build_envelope(self, record: SubscriptionLike, event: dict[str, Any]) -> str:
        body = {
            "schema_version": 1,
            "source": "xtquant-proxy",
            "subscription_id": record.subscription_id,
            "subscription_type": record.subscription_type,
            "mode": self.settings.xtquant.mode.value,
            "published_at_ms": int(time.time() * 1000),
            "event": event,
        }
        return json.dumps(body, ensure_ascii=False, separators=(",", ":"))

    def _record_error(self, message: str, *, bypass_circuit: bool = False) -> None:
        with self._lock:
            self._publish_errors += 1
            self._consecutive_failures += 1
            if (
                self.config.circuit_breaker_enabled
                and not bypass_circuit
                and self._consecutive_failures >= self.config.circuit_breaker_failure_threshold
            ):
                self._circuit_open_until = time.monotonic() + self.config.circuit_breaker_cooldown_seconds
                logger.warning(
                    f"redis circuit breaker opened: failures={self._consecutive_failures}, "
                    f"cooldown_seconds={self.config.circuit_breaker_cooldown_seconds}"
                )
        if self.config.fail_open:
            logger.warning(message)
            return
        logger.error(message)
        raise RuntimeError(message)
