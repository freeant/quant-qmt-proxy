from __future__ import annotations

import json
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
        self._publish_total = 0
        self._publish_errors = 0

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
        client = self._get_client()
        if client is None:
            self._record_error("redis client unavailable")
            return

        stream_key = self.build_stream_key(record.subscription_id, record.subscription_type)
        payload = self._build_envelope(record, event)
        maxlen = self._maxlen_for(record)
        try:
            client.xadd(
                stream_key,
                {"payload": payload},
                maxlen=maxlen,
                approximate=True,
            )
            self._publish_total += 1
        except Exception as exc:
            self._record_error(f"redis xadd failed: stream={stream_key}, error={exc}")

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

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None

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

    def _record_error(self, message: str) -> None:
        self._publish_errors += 1
        if self.config.fail_open:
            logger.warning(message)
            return
        logger.error(message)
        raise RuntimeError(message)
