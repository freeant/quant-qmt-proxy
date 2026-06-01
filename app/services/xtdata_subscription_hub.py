from __future__ import annotations

import asyncio
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Iterator

from app.config import Settings, XTQuantMode
from app.services.contracts import QuoteSubscriptionSpec, WholeQuoteSubscriptionSpec
from app.services.redis_stream_sink import RedisStreamSink
from app.services.xtdata_gateway import XTQUANT_DATA_AVAILABLE, XtDataGateway, to_epoch_ms
from app.utils.exceptions import DataServiceException
from app.utils.logger import logger

try:
    import xtquant.xtdata as xtdata
except ImportError:
    xtdata = None


@dataclass
class SubscriptionRecord:
    subscription_id: str
    subscription_type: str
    persistent: bool
    period: str
    symbols: list[str] = field(default_factory=list)
    markets: list[str] = field(default_factory=list)
    start_time: str = ""
    adjust_type: str = "none"
    count: int = 0
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    native_subids: list[int] = field(default_factory=list)
    consumer_queues: dict[str, queue.Queue] = field(default_factory=dict)
    consumer_drop_counts: dict[str, int] = field(default_factory=dict)
    active: bool = True


class XtDataSubscriptionHub:
    def __init__(
        self,
        settings: Settings,
        gateway: XtDataGateway,
        redis_sink: RedisStreamSink | None = None,
    ):
        self.settings = settings
        self.gateway = gateway
        self.redis_sink = redis_sink
        self._lock = threading.RLock()
        self._runner_lock = threading.Lock()
        self._subscriptions: dict[str, SubscriptionRecord] = {}
        self._runner_started = False
        self._runner_thread: threading.Thread | None = None
        self._runner_last_error: str | None = None

    def _start_runtime_if_needed(self) -> None:
        if self.settings.xtquant.mode == XTQuantMode.MOCK:
            return
        if not XTQUANT_DATA_AVAILABLE:
            return
        self.gateway.ensure_ready()
        with self._runner_lock:
            if self._runner_started and self._runner_thread and self._runner_thread.is_alive():
                return

            def worker() -> None:
                try:
                    xtdata.run()
                except Exception as exc:
                    self._runner_last_error = str(exc)
                    logger.error(f"xtdata.run stopped unexpectedly: {exc}")
                finally:
                    with self._runner_lock:
                        self._runner_started = False
                        self._runner_thread = None

            self._runner_last_error = None
            self._runner_thread = threading.Thread(
                target=worker,
                daemon=True,
                name="xtdata-subscription-runner",
            )
            self._runner_thread.start()
            self._runner_started = True
            logger.info("xtdata subscription runner started")

    def create_persistent_quote_subscription(self, spec: QuoteSubscriptionSpec) -> str:
        return self._create_quote_subscription(spec, persistent=True)

    def create_persistent_whole_quote_subscription(self, spec: WholeQuoteSubscriptionSpec) -> str:
        return self._create_whole_quote_subscription(spec, persistent=True)

    def stream_ephemeral_quote(
        self,
        spec: QuoteSubscriptionSpec,
        stop_checker: Callable[[], bool] | None = None,
    ) -> Iterator[dict[str, Any]]:
        subscription_id = self._create_quote_subscription(spec, persistent=False)
        try:
            yield from self.stream_blocking(subscription_id, stop_checker=stop_checker)
        finally:
            self.delete_subscription(subscription_id)

    def stream_ephemeral_whole_quote(
        self,
        spec: WholeQuoteSubscriptionSpec,
        stop_checker: Callable[[], bool] | None = None,
    ) -> Iterator[dict[str, Any]]:
        subscription_id = self._create_whole_quote_subscription(spec, persistent=False)
        try:
            yield from self.stream_blocking(subscription_id, stop_checker=stop_checker)
        finally:
            self.delete_subscription(subscription_id)

    def stream_blocking(
        self,
        subscription_id: str,
        stop_checker: Callable[[], bool] | None = None,
    ) -> Iterator[dict[str, Any]]:
        consumer_id, consumer_queue = self._register_consumer(subscription_id)
        record = self._get_record(subscription_id)
        try:
            if self.settings.xtquant.mode == XTQuantMode.MOCK:
                while record.active and (stop_checker is None or stop_checker()):
                    event = self._mock_event(record)
                    if self._should_publish_redis_in_stream_loop(record):
                        self._publish_redis(record, event)
                    yield event
                    time.sleep(1.0)
                return

            while record.active and (stop_checker is None or stop_checker()):
                try:
                    yield consumer_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
        finally:
            self._unregister_consumer(subscription_id, consumer_id)

    async def stream_async(self, subscription_id: str) -> AsyncIterator[dict[str, Any]]:
        consumer_id, consumer_queue = self._register_consumer(subscription_id)
        record = self._get_record(subscription_id)
        try:
            if self.settings.xtquant.mode == XTQuantMode.MOCK:
                while record.active:
                    event = self._mock_event(record)
                    if self._should_publish_redis_in_stream_loop(record):
                        self._publish_redis(record, event)
                    yield event
                    await asyncio.sleep(1.0)
                return

            while record.active:
                try:
                    item = await asyncio.to_thread(consumer_queue.get, True, 1.0)
                    yield item
                except queue.Empty:
                    continue
        finally:
            self._unregister_consumer(subscription_id, consumer_id)

    def delete_subscription(self, subscription_id: str) -> bool:
        with self._lock:
            record = self._subscriptions.pop(subscription_id, None)
        if not record:
            return False
        record.active = False
        self._unsubscribe_native(record)
        if self.redis_sink is not None:
            self.redis_sink.on_subscription_deleted(record)
        logger.info(f"deleted subscription: id={subscription_id}, type={record.subscription_type}")
        return True

    def get_subscription_info(self, subscription_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._subscriptions.get(subscription_id)
            if not record:
                return None
            return self._serialize_record(record)

    def list_subscriptions(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._serialize_record(record) for record in self._subscriptions.values()]

    def shutdown(self) -> None:
        with self._lock:
            subscription_ids = list(self._subscriptions.keys())
        for subscription_id in subscription_ids:
            self.delete_subscription(subscription_id)
        if self.redis_sink is not None:
            self.redis_sink.close()

    def _create_quote_subscription(self, spec: QuoteSubscriptionSpec, persistent: bool) -> str:
        if not spec.symbols:
            raise DataServiceException("symbols must not be empty", error_code="EMPTY_SYMBOLS")
        if spec.count < -1:
            raise DataServiceException("subscription count must be -1 or greater", error_code="INVALID_SUBSCRIPTION_COUNT")
        if spec.period == "tick" and spec.count < 0:
            raise DataServiceException(
                "tick subscriptions do not allow full-history replay; use count >= 0",
                error_code="INVALID_SUBSCRIPTION_COUNT",
            )
        subscription_id = f"quote_{uuid.uuid4().hex[:16]}"
        record = SubscriptionRecord(
            subscription_id=subscription_id,
            subscription_type="quote",
            persistent=persistent,
            symbols=[symbol.strip().upper() for symbol in spec.symbols if symbol.strip()],
            period=spec.period,
            start_time=spec.start_time,
            adjust_type=spec.adjust_type,
            count=spec.count,
        )
        with self._lock:
            self._ensure_subscription_capacity_locked()
            self._subscriptions[subscription_id] = record
        try:
            self._subscribe_native_quote(record)
        except Exception:
            with self._lock:
                failed_record = self._subscriptions.pop(subscription_id, None)
                if failed_record is not None:
                    failed_record.active = False
            raise
        logger.info(
            f"created quote subscription: id={subscription_id}, symbols={record.symbols}, period={record.period}, count={record.count}, persistent={persistent}"
        )
        self._start_mock_redis_feeder_if_needed(record)
        self._notify_subscription_ready(record)
        return subscription_id

    def _create_whole_quote_subscription(self, spec: WholeQuoteSubscriptionSpec, persistent: bool) -> str:
        if not self.settings.xtquant.data.whole_quote_enabled:
            raise DataServiceException("whole quote subscriptions are disabled by configuration", error_code="WHOLE_QUOTE_DISABLED")
        if self.settings.xtquant.mode == XTQuantMode.MOCK and not persistent:
            logger.info("mock mode whole quote stream enabled for local validation")
        subscription_id = f"whole_{uuid.uuid4().hex[:16]}"
        record = SubscriptionRecord(
            subscription_id=subscription_id,
            subscription_type="whole_quote",
            persistent=persistent,
            markets=[market.upper() for market in spec.markets] or ["SH", "SZ"],
            period="tick",
        )
        with self._lock:
            self._ensure_subscription_capacity_locked()
            self._subscriptions[subscription_id] = record
        try:
            self._subscribe_native_whole_quote(record)
        except Exception:
            with self._lock:
                failed_record = self._subscriptions.pop(subscription_id, None)
                if failed_record is not None:
                    failed_record.active = False
            raise
        logger.info(
            f"created whole-quote subscription: id={subscription_id}, markets={record.markets}, persistent={persistent}"
        )
        self._start_mock_redis_feeder_if_needed(record)
        self._notify_subscription_ready(record)
        return subscription_id

    def _notify_subscription_ready(self, record: SubscriptionRecord) -> None:
        if self.redis_sink is not None:
            self.redis_sink.publish_subscription_ready(record)

    def _start_mock_redis_feeder_if_needed(self, record: SubscriptionRecord) -> None:
        if self.settings.xtquant.mode != XTQuantMode.MOCK:
            return
        if not record.persistent:
            return
        if self.redis_sink is None or not self.redis_sink.should_mirror(record):
            return

        def worker() -> None:
            while record.active:
                event = self._mock_event(record)
                self._publish_redis(record, event)
                time.sleep(1.0)

        threading.Thread(
            target=worker,
            daemon=True,
            name=f"mock-redis-feeder-{record.subscription_id[:8]}",
        ).start()

    def _ensure_subscription_capacity_locked(self) -> None:
        limit = self.settings.xtquant.data.max_subscriptions
        if limit <= 0:
            return
        active_count = sum(1 for record in self._subscriptions.values() if record.active)
        if active_count >= limit:
            raise DataServiceException(
                f"subscription limit reached: max_subscriptions={limit}",
                error_code="MAX_SUBSCRIPTIONS_EXCEEDED",
            )

    def _subscribe_native_quote(self, record: SubscriptionRecord) -> None:
        if self.settings.xtquant.mode == XTQuantMode.MOCK:
            return
        if not XTQUANT_DATA_AVAILABLE:
            raise DataServiceException("xtquant.xtdata is unavailable", error_code="XTDATA_UNAVAILABLE")
        self._start_runtime_if_needed()

        def callback(payload: dict[str, Any]) -> None:
            for event in self._normalize_payload(record.period, payload):
                self._fanout(record.subscription_id, event)

        native_subids = []
        try:
            for symbol in record.symbols:
                subid = xtdata.subscribe_quote2(
                    stock_code=symbol,
                    period=record.period,
                    start_time=record.start_time,
                    end_time="",
                    count=record.count,
                    dividend_type=record.adjust_type,
                    callback=callback,
                )
                if subid < 0:
                    raise DataServiceException("xtdata quote subscription failed", error_code="SUBSCRIPTION_FAILED")
                native_subids.append(subid)
            record.native_subids = native_subids
            logger.info(
                f"native quote subscription ready: id={record.subscription_id}, subids={record.native_subids}"
            )
        except Exception:
            self._unsubscribe_native(record)
            raise

    def _subscribe_native_whole_quote(self, record: SubscriptionRecord) -> None:
        if self.settings.xtquant.mode == XTQuantMode.MOCK:
            return
        if not XTQUANT_DATA_AVAILABLE:
            raise DataServiceException("xtquant.xtdata is unavailable", error_code="XTDATA_UNAVAILABLE")
        self._start_runtime_if_needed()

        def callback(payload: dict[str, Any]) -> None:
            for event in self._normalize_payload("tick", payload):
                self._fanout(record.subscription_id, event)

        subid = xtdata.subscribe_whole_quote(record.markets or ["SH", "SZ"], callback=callback)
        if subid < 0:
            raise DataServiceException("xtdata whole-quote subscription failed", error_code="SUBSCRIPTION_FAILED")
        record.native_subids = [subid]
        logger.info(
            f"native whole-quote subscription ready: id={record.subscription_id}, subids={record.native_subids}"
        )

    def _unsubscribe_native(self, record: SubscriptionRecord) -> None:
        if self.settings.xtquant.mode == XTQuantMode.MOCK:
            return
        if not XTQUANT_DATA_AVAILABLE:
            return
        for subid in list(record.native_subids):
            try:
                xtdata.unsubscribe_quote(subid)
            except Exception as exc:
                logger.warning(f"unsubscribe_quote failed for {subid}: {exc}")
        record.native_subids = []

    def _register_consumer(self, subscription_id: str) -> tuple[str, queue.Queue]:
        consumer_id = uuid.uuid4().hex
        consumer_queue: queue.Queue = queue.Queue(maxsize=self.settings.xtquant.data.max_queue_size)
        with self._lock:
            record = self._get_record(subscription_id)
            record.consumer_queues[consumer_id] = consumer_queue
            record.consumer_drop_counts[consumer_id] = 0
        return consumer_id, consumer_queue

    def _unregister_consumer(self, subscription_id: str, consumer_id: str) -> None:
        with self._lock:
            record = self._subscriptions.get(subscription_id)
            if not record:
                return
            record.consumer_queues.pop(consumer_id, None)
            record.consumer_drop_counts.pop(consumer_id, None)
            should_cleanup = not record.persistent and not record.consumer_queues
        if should_cleanup:
            self.delete_subscription(subscription_id)

    def _fanout(self, subscription_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            record = self._subscriptions.get(subscription_id)
            if not record:
                return
            consumer_queues = list(record.consumer_queues.items())
        for consumer_id, consumer_queue in consumer_queues:
            try:
                consumer_queue.put_nowait(event)
            except queue.Full:
                try:
                    consumer_queue.get_nowait()
                except queue.Empty:
                    pass
                consumer_queue.put_nowait(event)
                with self._lock:
                    latest_record = self._subscriptions.get(subscription_id)
                    if not latest_record:
                        continue
                    dropped_total = latest_record.consumer_drop_counts.get(consumer_id, 0) + 1
                    latest_record.consumer_drop_counts[consumer_id] = dropped_total
                if dropped_total == 1 or dropped_total % 100 == 0:
                    logger.warning(
                        f"subscription queue overflow: subscription_id={subscription_id}, consumer_id={consumer_id}, dropped_total={dropped_total}"
                    )

        self._publish_redis(record, event)

    def _publish_redis(self, record: SubscriptionRecord, event: dict[str, Any]) -> None:
        if self.redis_sink is not None:
            self.redis_sink.publish(record, event)

    def _should_publish_redis_in_stream_loop(self, record: SubscriptionRecord) -> bool:
        if not record.persistent:
            return True
        if (
            self.settings.xtquant.mode == XTQuantMode.MOCK
            and self.redis_sink is not None
            and self.redis_sink.should_mirror(record)
        ):
            return False
        return True

    def _normalize_payload(self, period: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        events: list[dict[str, Any]] = []
        for symbol, value in payload.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                for item in value:
                    events.append(self._build_event(symbol, period, item))
            else:
                events.append(self._build_event(symbol, period, value))
        return events

    def _build_event(self, symbol: str, period: str, payload: Any) -> dict[str, Any]:
        event_time_ms = int(time.time() * 1000)
        if period == "tick":
            return {
                "symbol": symbol,
                "period": period,
                "event_time_ms": event_time_ms,
                "payload_type": "tick",
                "data": self.gateway._normalize_tick_payload(payload),
            }

        bar_time_ms = event_time_ms
        bar: dict[str, Any] = {}
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized_key = self.gateway._snake_case_field(key)
                if normalized_key in {"time", "time_ms"}:
                    bar_time_ms = to_epoch_ms(value)
                    continue
                normalized_value = value
                if normalized_key in {"volume", "open_interest", "suspend_flag"}:
                    try:
                        normalized_value = int(value or 0)
                    except Exception:
                        normalized_value = 0
                elif normalized_key != "time_ms":
                    try:
                        normalized_value = float(value or 0.0)
                    except Exception:
                        normalized_value = 0.0
                bar[normalized_key] = normalized_value
        bar["time_ms"] = bar_time_ms
        return {
            "symbol": symbol,
            "period": period,
            "event_time_ms": event_time_ms,
            "payload_type": "kline",
            "data": bar,
        }

    def _serialize_record(self, record: SubscriptionRecord) -> dict[str, Any]:
        payload = {
            "subscription_id": record.subscription_id,
            "subscription_type": record.subscription_type,
            "persistent": record.persistent,
            "symbols": record.symbols,
            "markets": record.markets,
            "period": record.period,
            "start_time": record.start_time,
            "adjust_type": record.adjust_type,
            "count": record.count,
            "created_at_ms": record.created_at_ms,
            "native_subids": list(record.native_subids),
            "consumer_count": len(record.consumer_queues),
            "active": record.active,
        }
        if self.redis_sink is not None and self.redis_sink.should_mirror(record):
            payload["redis_stream_key"] = self.redis_sink.build_stream_key(
                record.subscription_id,
                record.subscription_type,
            )
        return payload

    def _get_record(self, subscription_id: str) -> SubscriptionRecord:
        record = self._subscriptions.get(subscription_id)
        if not record:
            raise DataServiceException(
                f"subscription not found: {subscription_id}",
                error_code="SUBSCRIPTION_NOT_FOUND",
            )
        return record

    def _mock_event(self, record: SubscriptionRecord) -> dict[str, Any]:
        symbol = record.symbols[0] if record.symbols else "000001.SZ"
        now_ms = int(time.time() * 1000)
        if record.subscription_type == "whole_quote" or record.period == "tick":
            return {
                "symbol": symbol,
                "period": "tick",
                "event_time_ms": now_ms,
                "payload_type": "tick",
                "data": self.gateway._mock_tick_payload(symbol),
            }
        return {
            "symbol": symbol,
            "period": record.period,
            "event_time_ms": now_ms,
            "payload_type": "kline",
            "data": {
                "time_ms": now_ms,
                "open": 100.0,
                "high": 101.0,
                "low": 99.5,
                "close": 100.5,
                "volume": 1000,
                "amount": 100500.0,
                "settle": 100.3,
                "open_interest": 500,
                "pre_close": 99.8,
                "suspend_flag": 0,
            },
        }
