from __future__ import annotations

import asyncio

import pytest
from starlette.websockets import WebSocketDisconnect

import app.config as config_module
from app.dependencies import get_ui_subscription_service
from tests.conftest import RestTestContext


WEBSOCKET_TESTED_ENDPOINTS = {"/ws/quote/{subscription_id}"}


def _create_subscription(rest_test_context: RestTestContext, path: str, body: dict) -> str:
    response = rest_test_context.client.post(path, json=body, headers=rest_test_context.headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    return payload["data"]["subscription_id"]


def test_rest_and_websocket_quote_subscription_flow(rest_test_context: RestTestContext):
    subscription_id = _create_subscription(
        rest_test_context,
        "/api/v1/data/subscriptions/quote",
        {"symbols": ["000001.SZ"], "period": "tick"},
    )

    with rest_test_context.client.websocket_connect(
        f"/ws/quote/{subscription_id}?token={rest_test_context.runtime.api_key}"
    ) as websocket:
        connected = websocket.receive_json()
        message = websocket.receive_json()

    assert connected["type"] == "connected"
    if rest_test_context.runtime.is_real:
        assert message["type"] in {"quote", "heartbeat"}
        if message["type"] == "quote":
            assert message["data"]["symbol"] == "000001.SZ"
        else:
            assert message["subscription_id"] == subscription_id
    else:
        assert message["type"] == "quote"
        assert message["data"]["symbol"] == "000001.SZ"


def test_rest_and_websocket_whole_quote_subscription_flow(rest_test_context: RestTestContext):
    subscription_id = _create_subscription(
        rest_test_context,
        "/api/v1/data/subscriptions/whole-quote",
        {"markets": ["SH", "SZ"]},
    )

    with rest_test_context.client.websocket_connect(
        f"/ws/quote/{subscription_id}?token={rest_test_context.runtime.api_key}"
    ) as websocket:
        connected = websocket.receive_json()
        quote = websocket.receive_json()

    assert connected["type"] == "connected"
    assert quote["type"] == "quote"
    assert quote["data"]["period"] == "tick"


def test_websocket_rejects_missing_or_invalid_token(rest_test_context: RestTestContext):
    subscription_id = _create_subscription(
        rest_test_context,
        "/api/v1/data/subscriptions/quote",
        {"symbols": ["000001.SZ"], "period": "tick"},
    )

    with pytest.raises(WebSocketDisconnect):
        with rest_test_context.client.websocket_connect(f"/ws/quote/{subscription_id}"):
            pass

    with pytest.raises(WebSocketDisconnect):
        with rest_test_context.client.websocket_connect(f"/ws/quote/{subscription_id}?token=wrong-token"):
            pass


def test_websocket_rejects_unknown_subscription(rest_test_context: RestTestContext):
    with rest_test_context.client.websocket_connect(
        f"/ws/quote/missing-subscription?token={rest_test_context.runtime.api_key}"
    ) as websocket:
        message = websocket.receive_json()
        assert message["type"] == "error"
        assert "missing-subscription" in message["message"]
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_websocket_sends_heartbeat_when_subscription_stream_is_idle(rest_test_context: RestTestContext):
    class SlowSubscriptionService:
        def get_subscription_info(self, subscription_id: str):
            return {"subscription_id": subscription_id}

        async def stream_subscription(self, subscription_id: str):
            while True:
                await asyncio.sleep(1)
                yield {"symbol": "000001.SZ"}

    rest_test_context.client.app.dependency_overrides[get_ui_subscription_service] = lambda: SlowSubscriptionService()
    config_module._settings_instance.xtquant.data.heartbeat_interval = 0.01

    try:
        with rest_test_context.client.websocket_connect(
            f"/ws/quote/slow-heartbeat?token={rest_test_context.runtime.api_key}"
        ) as websocket:
            connected = websocket.receive_json()
            heartbeat = websocket.receive_json()

        assert connected["type"] == "connected"
        assert heartbeat["type"] == "heartbeat"
        assert heartbeat["subscription_id"] == "slow-heartbeat"
    finally:
        rest_test_context.client.app.dependency_overrides.clear()
        config_module._settings_instance.xtquant.data.heartbeat_interval = 60
