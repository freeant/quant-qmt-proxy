from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from fakeredis import FakeRedis

from app.config import Settings
from app.services.contracts import QuoteSubscriptionSpec, WholeQuoteSubscriptionSpec
from app.services.redis_stream_sink import RedisStreamSink
from app.services.xtdata_gateway import XtDataGateway
from app.services.xtdata_subscription_hub import XtDataSubscriptionHub


@dataclass
class _Record:
    subscription_id: str
    subscription_type: str
    persistent: bool


def build_redis_settings(**redis_overrides) -> Settings:
    redis_config = {
        "enabled": True,
        "url": "redis://127.0.0.1:6379/0",
        "stream_prefix": "qmt",
        "maxlen": 10,
        "grace_ttl_seconds": 60,
        "delete_stream_on_unsubscribe": False,
        "mirror_mock": True,
        "mirror_ephemeral": False,
        "mirror_whole_quote": False,
    }
    redis_config.update(redis_overrides)
    return Settings(
        xtquant={"mode": "mock", "data": {"max_queue_size": 4, "max_subscriptions": 10}},
        redis=redis_config,
    )


def test_redis_stream_sink_xadd_and_envelope():
    settings = build_redis_settings()
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("quote_test123", "quote", True)
    event = {"symbol": "000001.SZ", "period": "tick", "payload_type": "tick", "data": {"last_price": 1.0}}

    sink.publish(record, event)

    entries = client.xrange("qmt:quote:quote_test123")
    assert len(entries) == 1
    envelope = json.loads(entries[0][1]["payload"])
    assert envelope["schema_version"] == 1
    assert envelope["subscription_id"] == "quote_test123"
    assert envelope["event"]["symbol"] == "000001.SZ"


def test_redis_stream_sink_respects_maxlen():
    settings = build_redis_settings(maxlen=2)
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("quote_trim", "quote", True)

    for index in range(5):
        sink.publish(record, {"symbol": "000001.SZ", "index": index})

    assert len(client.xrange("qmt:quote:quote_trim")) <= 3


def test_redis_stream_sink_expire_on_delete():
    settings = build_redis_settings(grace_ttl_seconds=30)
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("quote_expire", "quote", True)
    sink.publish(record, {"symbol": "000001.SZ"})

    sink.on_subscription_deleted(record)

    assert client.ttl("qmt:quote:quote_expire") > 0


def test_redis_stream_sink_skips_ephemeral_by_default():
    settings = build_redis_settings()
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("quote_ephemeral", "quote", False)

    sink.publish(record, {"symbol": "000001.SZ"})

    assert client.xrange("qmt:quote:quote_ephemeral") == []


def test_hub_serializes_redis_stream_key():
    settings = build_redis_settings()
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings), sink)

    subscription_id = hub.create_persistent_quote_subscription(
        QuoteSubscriptionSpec(symbols=["000001.SZ"], period="tick")
    )
    info = hub.get_subscription_info(subscription_id)

    assert info is not None
    assert info["redis_stream_key"] == f"qmt:quote:{subscription_id}"
    hub.delete_subscription(subscription_id)


def test_readiness_reports_redis_disabled_by_default(rest_test_context):
    response = rest_test_context.client.get("/health/ready")
    payload = response.json()
    assert payload["data"]["checks"]["redis"]["status"] == "disabled"


def test_redis_stream_sink_publishes_subscription_ready():
    settings = build_redis_settings(publish_subscription_ready=True)
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("quote_ready", "quote", True)

    sink.publish_subscription_ready(record)

    entries = client.xrange("qmt:quote:quote_ready")
    assert len(entries) == 1
    envelope = json.loads(entries[0][1]["payload"])
    assert envelope["event"]["payload_type"] == "subscription_ready"
    assert envelope["event"]["data"]["redis_stream_key"] == "qmt:quote:quote_ready"


def test_redis_stream_sink_mirror_ephemeral_when_enabled():
    settings = build_redis_settings(mirror_ephemeral=True)
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("quote_ephemeral_on", "quote", False)

    sink.publish(record, {"symbol": "000001.SZ", "payload_type": "tick", "data": {}})

    assert len(client.xrange("qmt:quote:quote_ephemeral_on")) == 1


def test_redis_stream_sink_mirror_whole_quote():
    settings = Settings(
        xtquant={"mode": "mock", "data": {"max_queue_size": 4, "max_subscriptions": 10, "whole_quote_enabled": True}},
        redis={
            "enabled": True,
            "mirror_mock": True,
            "mirror_whole_quote": True,
            "whole_quote_maxlen": 5,
            "publish_subscription_ready": False,
        },
    )
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("whole_test", "whole_quote", True)

    sink.publish(record, {"symbol": "000001.SZ", "payload_type": "tick", "data": {"last_price": 1.0}})

    assert len(client.xrange("qmt:whole:whole_test")) == 1


def test_hub_publishes_subscription_ready_on_create():
    settings = build_redis_settings(publish_subscription_ready=True)
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings), sink)

    subscription_id = hub.create_persistent_quote_subscription(
        QuoteSubscriptionSpec(symbols=["600000.SH"], period="tick")
    )
    stream_key = f"qmt:quote:{subscription_id}"
    entries = client.xrange(stream_key)
    ready_messages = [
        json.loads(entry[1]["payload"])
        for entry in entries
        if json.loads(entry[1]["payload"])["event"]["payload_type"] == "subscription_ready"
    ]
    assert ready_messages
    assert ready_messages[0]["event"]["data"]["redis_stream_key"] == stream_key
    hub.delete_subscription(subscription_id)


def test_hub_whole_quote_redis_stream_key_when_enabled():
    settings = Settings(
        xtquant={"mode": "mock", "data": {"max_queue_size": 4, "max_subscriptions": 10, "whole_quote_enabled": True}},
        redis={
            "enabled": True,
            "mirror_mock": True,
            "mirror_whole_quote": True,
            "publish_subscription_ready": False,
        },
    )
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings), sink)

    subscription_id = hub.create_persistent_whole_quote_subscription(
        WholeQuoteSubscriptionSpec(markets=["SH", "SZ"])
    )
    info = hub.get_subscription_info(subscription_id)
    assert info is not None
    assert info["redis_stream_key"] == f"qmt:whole:{subscription_id}"
    hub.delete_subscription(subscription_id)


def test_redis_circuit_breaker_opens_and_skips_publish():
    settings = build_redis_settings(
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=2,
        circuit_breaker_cooldown_seconds=60,
    )

    class FailingRedis:
        def xadd(self, *args, **kwargs):
            raise ConnectionError("boom")

        def ping(self):
            return True

    sink = RedisStreamSink(settings, client=FailingRedis())
    record = _Record("quote_cb", "quote", True)

    sink.publish(record, {"symbol": "000001.SZ"})
    sink.publish(record, {"symbol": "000001.SZ"})
    assert sink.get_stats()["circuit_open"] is True

    sink.publish(record, {"symbol": "000001.SZ"})
    stats = sink.get_stats()
    assert stats["publish_skipped_circuit"] >= 1
    assert stats["publish_errors"] >= 2


def test_redis_get_stats_tracks_successful_publish():
    settings = build_redis_settings()
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("quote_stats", "quote", True)

    sink.publish(record, {"symbol": "000001.SZ", "payload_type": "tick", "data": {}})

    stats = sink.get_stats()
    assert stats["publish_total"] == 1
    assert stats["publish_errors"] == 0
    assert stats["circuit_open"] is False
    assert stats["last_publish_latency_ms"] >= 0


def test_redis_symbol_stream_dual_write():
    settings = build_redis_settings(mirror_symbol_streams=True, symbol_stream_maxlen=5)
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("quote_symbol", "quote", True)
    event = {"symbol": "600000.SH", "payload_type": "tick", "data": {"last_price": 10.0}}

    sink.publish(record, event)

    assert len(client.xrange("qmt:quote:quote_symbol")) == 1
    assert len(client.xrange("qmt:symbol:600000.SH")) == 1
    symbol_envelope = json.loads(client.xrange("qmt:symbol:600000.SH")[0][1]["payload"])
    assert symbol_envelope["subscription_id"] == "quote_symbol"
    assert symbol_envelope["event"]["symbol"] == "600000.SH"


def test_redis_symbol_stream_skipped_when_disabled():
    settings = build_redis_settings(mirror_symbol_streams=False)
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    record = _Record("quote_no_symbol", "quote", True)

    sink.publish(record, {"symbol": "600000.SH", "payload_type": "tick", "data": {}})

    assert len(client.xrange("qmt:quote:quote_no_symbol")) == 1
    assert client.xrange("qmt:symbol:600000.SH") == []


def test_hub_serializes_redis_symbol_stream_keys():
    settings = build_redis_settings(mirror_symbol_streams=True, publish_subscription_ready=False)
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    hub = XtDataSubscriptionHub(settings, XtDataGateway(settings), sink)

    subscription_id = hub.create_persistent_quote_subscription(
        QuoteSubscriptionSpec(symbols=["000001.SZ", "600000.SH"], period="tick")
    )
    info = hub.get_subscription_info(subscription_id)

    assert info is not None
    assert info["redis_symbol_stream_keys"] == {
        "000001.SZ": "qmt:symbol:000001.SZ",
        "600000.SH": "qmt:symbol:600000.SH",
    }
    hub.delete_subscription(subscription_id)


def test_redis_trading_event_publish():
    settings = build_redis_settings(mirror_trading_events=True, trading_stream_maxlen=10)
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    session_id = "session_mock_001"
    event = {
        "event_time_ms": 1,
        "event_type": "order_update",
        "payload": {"order_id": "mock_1001", "stock_code": "000001.SZ"},
    }

    sink.publish_trading_event(session_id, event)

    stream_key = f"qmt:trading:{session_id}"
    entries = client.xrange(stream_key)
    assert len(entries) == 1
    envelope = json.loads(entries[0][1]["payload"])
    assert envelope["session_id"] == session_id
    assert envelope["event"]["event_type"] == "order_update"


def test_redis_trading_session_close_expires_stream():
    settings = build_redis_settings(
        mirror_trading_events=True,
        trading_stream_grace_ttl_seconds=45,
    )
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    session_id = "session_close_001"
    sink.publish_trading_event(session_id, {"event_type": "asset_update", "payload": {}})

    sink.on_trading_session_closed(session_id)

    assert client.ttl(f"qmt:trading:{session_id}") > 0


def test_trading_session_manager_publishes_redis_events():
    from app.services.contracts import OpenSessionCommand, SubmitStockOrderCommand
    from app.services.trading_session_manager import TradingSessionManager

    settings = Settings(
        xtquant={"mode": "mock", "data": {"max_queue_size": 4, "max_subscriptions": 10}},
        redis={
            "enabled": True,
            "mirror_mock": True,
            "mirror_trading_events": True,
            "publish_subscription_ready": False,
        },
    )
    client = FakeRedis(decode_responses=True)
    sink = RedisStreamSink(settings, client=client)
    manager = TradingSessionManager(settings, redis_sink=sink)
    session = manager.open_session(OpenSessionCommand(account_id="mock-account"))

    assert session["redis_trading_stream_key"] == f"qmt:trading:{session['session_id']}"

    manager.submit_stock_order(
        SubmitStockOrderCommand(
            session_id=session["session_id"],
            stock_code="000001.SZ",
            side=23,
            price_type=11,
            volume=100,
            price=10.5,
        )
    )

    stream_key = session["redis_trading_stream_key"]
    entries = client.xrange(stream_key)
    assert entries
    envelope = json.loads(entries[-1][1]["payload"])
    assert envelope["event"]["event_type"] == "order_update"

    manager.close_session(session["session_id"])
    assert client.ttl(stream_key) > 0


def test_redis_ssl_kwargs_passed_to_from_url(monkeypatch):
    settings = build_redis_settings(ssl_enabled=True, ssl_cert_reqs="none", url="redis://127.0.0.1:6379/0")
    captured: dict = {}

    def fake_from_url(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeRedis(decode_responses=True)

    monkeypatch.setattr("app.services.redis_stream_sink.redis.from_url", fake_from_url)
    sink = RedisStreamSink(settings)
    assert sink.ping() is True
    assert captured["kwargs"]["ssl"] is True
    import ssl

    assert captured["kwargs"]["ssl_cert_reqs"] == ssl.CERT_NONE


def test_redis_sentinel_client_created(monkeypatch):
    settings = build_redis_settings(
        sentinel_enabled=True,
        sentinel_hosts=["127.0.0.1:26379", "127.0.0.2:26379"],
        sentinel_service_name="mymaster",
        sentinel_db=1,
    )
    captured: dict = {}

    class FakeSentinel:
        def __init__(self, hosts, **kwargs):
            captured["hosts"] = hosts
            captured["sentinel_kwargs"] = kwargs

        def master_for(self, service_name, **kwargs):
            captured["service_name"] = service_name
            captured["master_kwargs"] = kwargs
            return FakeRedis(decode_responses=True)

    monkeypatch.setattr("app.services.redis_stream_sink.Sentinel", FakeSentinel)
    sink = RedisStreamSink(settings)
    assert sink.ping() is True
    assert captured["hosts"] == [("127.0.0.1", 26379), ("127.0.0.2", 26379)]
    assert captured["service_name"] == "mymaster"
    assert captured["master_kwargs"]["db"] == 1
