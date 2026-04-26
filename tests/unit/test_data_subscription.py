import threading
import time
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.services.contracts import QuoteSubscriptionSpec, WholeQuoteSubscriptionSpec
from app.services.xtdata_gateway import to_epoch_ms
from app.services.xtdata_gateway import XtDataGateway
from app.services import xtdata_subscription_hub as subscription_hub_module
from app.services.xtdata_subscription_hub import XtDataSubscriptionHub
from app.utils.exceptions import DataServiceException


def build_mock_settings() -> Settings:
    return Settings(
        xtquant={
            "mode": "mock",
            "data": {"max_queue_size": 4, "max_subscriptions": 100, "whole_quote_enabled": True},
        }
    )


def test_persistent_quote_subscription_streams_mock_tick():
    settings = build_mock_settings()
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings))

    subscription_id = hub.create_persistent_quote_subscription(
        QuoteSubscriptionSpec(symbols=["000001.SZ"], period="tick")
    )
    info = hub.get_subscription_info(subscription_id)

    assert info is not None
    assert info["subscription_type"] == "quote"
    assert info["symbols"] == ["000001.SZ"]
    assert info["count"] == 0

    counter = {"count": 0}

    def stop_checker() -> bool:
        counter["count"] += 1
        return counter["count"] <= 1

    event = next(hub.stream_blocking(subscription_id, stop_checker=stop_checker))

    assert event["symbol"] == "000001.SZ"
    assert event["payload_type"] == "tick"
    assert "last_price" in event["data"]

    assert hub.delete_subscription(subscription_id) is True
    assert hub.get_subscription_info(subscription_id) is None


def test_ephemeral_quote_stream_auto_cleans_subscription():
    settings = build_mock_settings()
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings))

    counter = {"count": 0}

    def stop_checker() -> bool:
        counter["count"] += 1
        return counter["count"] <= 1

    iterator = hub.stream_ephemeral_quote(
        QuoteSubscriptionSpec(symbols=["600000.SH"], period="1d"),
        stop_checker=stop_checker,
    )
    event = next(iterator)
    iterator.close()

    assert event["symbol"] == "600000.SH"
    assert event["payload_type"] == "kline"
    assert hub.list_subscriptions() == []


def test_subscription_hub_does_not_eagerly_require_xtdata_ready():
    class FakeGateway:
        def __init__(self):
            self.ensure_ready_called = False

        def ensure_ready(self):
            self.ensure_ready_called = True

        def _normalize_tick_payload(self, payload):
            return payload

        def _snake_case_field(self, field: str) -> str:
            mapping = {
                "openInterest": "open_interest",
                "preClose": "pre_close",
                "suspendFlag": "suspend_flag",
            }
            return mapping.get(field, field)

        def _mock_tick_payload(self, symbol: str):
            return {"symbol": symbol}

    settings = Settings(xtquant={"mode": "dev", "data": {"max_queue_size": 4}})
    gateway = FakeGateway()
    XtDataSubscriptionHub(settings, gateway)

    assert gateway.ensure_ready_called is False


def test_build_event_maps_kline_payload_time_to_time_ms():
    settings = build_mock_settings()
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings))

    event = hub._build_event(
        "000001.SZ",
        "1d",
        {
            "time": "20250102103000",
            "open": 10.5,
            "high": 11.0,
            "volume": 1200,
        },
    )

    assert event["payload_type"] == "kline"
    assert event["data"]["time_ms"] == to_epoch_ms("20250102103000")
    assert "time" not in event["data"]
    assert event["data"]["volume"] == 1200


def test_quote_subscription_rejects_tick_full_history_replay():
    settings = build_mock_settings()
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings))

    with pytest.raises(DataServiceException) as exc:
        hub.create_persistent_quote_subscription(
            QuoteSubscriptionSpec(symbols=["000001.SZ"], period="tick", count=-1)
        )

    assert exc.value.error_code == "INVALID_SUBSCRIPTION_COUNT"


def test_real_quote_subscription_passes_count_to_xtdata(monkeypatch):
    class FakeGateway:
        def __init__(self):
            self.ensure_ready_called = False

        def ensure_ready(self):
            self.ensure_ready_called = True

        def _normalize_tick_payload(self, payload):
            return payload

        def _snake_case_field(self, field: str) -> str:
            return field

        def _mock_tick_payload(self, symbol: str):
            return {"symbol": symbol}

    calls: list[dict[str, object]] = []

    class FakeXtdata:
        @staticmethod
        def subscribe_quote2(**kwargs):
            calls.append(kwargs)
            return 1

        @staticmethod
        def unsubscribe_quote(subid):
            return None

    settings = Settings(xtquant={"mode": "dev", "data": {"max_queue_size": 4}})
    hub = XtDataSubscriptionHub(settings, FakeGateway())

    monkeypatch.setattr("app.services.xtdata_subscription_hub.XTQUANT_DATA_AVAILABLE", True)
    monkeypatch.setattr("app.services.xtdata_subscription_hub.xtdata", FakeXtdata)
    monkeypatch.setattr(hub, "_start_runtime_if_needed", lambda: None)

    subscription_id = hub.create_persistent_quote_subscription(
        QuoteSubscriptionSpec(symbols=["000001.SZ"], period="1d", count=7)
    )

    assert calls
    assert calls[0]["count"] == 7
    hub.delete_subscription(subscription_id)


def test_subscription_runner_starts_only_once_under_concurrent_calls(monkeypatch):
    class FakeGateway:
        def ensure_ready(self):
            return None

        def _normalize_tick_payload(self, payload):
            return payload

        def _snake_case_field(self, field: str) -> str:
            return field

        def _mock_tick_payload(self, symbol: str):
            return {"symbol": symbol}

    created_threads = []

    class FakeThread:
        def __init__(self, target=None, daemon=None, name=None):
            self.target = target
            self.daemon = daemon
            self.name = name
            self._alive = False
            created_threads.append(self)

        def start(self):
            self._alive = True

        def is_alive(self):
            return self._alive

    settings = Settings(xtquant={"mode": "dev", "data": {"max_queue_size": 4}})
    hub = XtDataSubscriptionHub(settings, FakeGateway())

    monkeypatch.setattr("app.services.xtdata_subscription_hub.XTQUANT_DATA_AVAILABLE", True)
    monkeypatch.setattr("app.services.xtdata_subscription_hub.xtdata", object())
    monkeypatch.setattr(
        "app.services.xtdata_subscription_hub.threading",
        SimpleNamespace(Thread=FakeThread),
    )

    barrier = threading.Barrier(3)

    def worker():
        barrier.wait()
        hub._start_runtime_if_needed()

    thread_a = threading.Thread(target=worker)
    thread_b = threading.Thread(target=worker)
    thread_a.start()
    thread_b.start()
    barrier.wait()
    thread_a.join(timeout=1)
    thread_b.join(timeout=1)

    assert len(created_threads) == 1


def test_subscription_queue_overflow_emits_warning(monkeypatch):
    settings = Settings(xtquant={"mode": "mock", "data": {"max_queue_size": 1}})
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings))
    subscription_id = hub.create_persistent_quote_subscription(
        QuoteSubscriptionSpec(symbols=["000001.SZ"], period="tick")
    )
    consumer_id, consumer_queue = hub._register_consumer(subscription_id)
    warnings: list[str] = []

    monkeypatch.setattr(subscription_hub_module.logger, "warning", lambda message: warnings.append(message))

    hub._fanout(subscription_id, {"seq": 1})
    hub._fanout(subscription_id, {"seq": 2})

    assert warnings
    assert "subscription queue overflow" in warnings[0]
    assert "subscription_id=" in warnings[0]
    assert consumer_queue.get_nowait()["seq"] == 2
    hub._unregister_consumer(subscription_id, consumer_id)
    hub.delete_subscription(subscription_id)


def test_subscription_limit_is_enforced():
    settings = Settings(
        xtquant={
            "mode": "mock",
            "data": {"max_queue_size": 4, "max_subscriptions": 1, "whole_quote_enabled": True},
        }
    )
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings))
    hub.create_persistent_quote_subscription(QuoteSubscriptionSpec(symbols=["000001.SZ"], period="tick"))

    with pytest.raises(DataServiceException) as exc:
        hub.create_persistent_quote_subscription(QuoteSubscriptionSpec(symbols=["600000.SH"], period="tick"))

    assert exc.value.error_code == "MAX_SUBSCRIPTIONS_EXCEEDED"


def test_whole_quote_subscription_requires_enable_flag():
    settings = Settings(
        xtquant={
            "mode": "mock",
            "data": {"max_queue_size": 4, "whole_quote_enabled": False},
        }
    )
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings))

    with pytest.raises(DataServiceException) as exc:
        hub.create_persistent_whole_quote_subscription(WholeQuoteSubscriptionSpec(markets=["SH", "SZ"]))

    assert exc.value.error_code == "WHOLE_QUOTE_DISABLED"


def test_failed_native_subscription_rolls_back_record(monkeypatch):
    settings = Settings(
        xtquant={
            "mode": "dev",
            "data": {"max_queue_size": 4, "max_subscriptions": 1, "whole_quote_enabled": True},
        }
    )
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings))

    monkeypatch.setattr(hub, "_subscribe_native_quote", lambda record: (_ for _ in ()).throw(DataServiceException("boom", "SUBSCRIPTION_FAILED")))

    with pytest.raises(DataServiceException) as exc:
        hub.create_persistent_quote_subscription(QuoteSubscriptionSpec(symbols=["000001.SZ"], period="tick"))

    assert exc.value.error_code == "SUBSCRIPTION_FAILED"
    assert hub.list_subscriptions() == []


def test_subscription_limit_is_atomic_under_concurrency(monkeypatch):
    settings = Settings(
        xtquant={
            "mode": "dev",
            "data": {"max_queue_size": 4, "max_subscriptions": 1, "whole_quote_enabled": True},
        }
    )
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings))
    release_first = threading.Event()
    created: list[str] = []
    errors: list[str] = []

    def fake_subscribe(record):
        created.append(record.subscription_id)
        release_first.wait(timeout=1)

    monkeypatch.setattr(hub, "_subscribe_native_quote", fake_subscribe)

    def worker(symbol: str):
        try:
            hub.create_persistent_quote_subscription(QuoteSubscriptionSpec(symbols=[symbol], period="tick"))
        except DataServiceException as exc:
            errors.append(exc.error_code or "UNKNOWN")

    thread_a = threading.Thread(target=worker, args=("000001.SZ",), daemon=True)
    thread_b = threading.Thread(target=worker, args=("600000.SH",), daemon=True)
    thread_a.start()
    time.sleep(0.05)
    thread_b.start()
    time.sleep(0.05)
    release_first.set()
    thread_a.join(timeout=1)
    thread_b.join(timeout=1)

    assert len(created) == 1
    assert errors == ["MAX_SUBSCRIPTIONS_EXCEEDED"]
    assert len(hub.list_subscriptions()) == 1
