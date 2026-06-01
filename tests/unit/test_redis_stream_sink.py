from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from fakeredis import FakeRedis

from app.config import Settings
from app.services.contracts import QuoteSubscriptionSpec
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
