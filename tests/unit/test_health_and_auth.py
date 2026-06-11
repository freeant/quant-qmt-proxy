from __future__ import annotations

import grpc
import pytest

from app.grpc_services.data_grpc_service import DataGrpcService
from app.grpc_services.trading_grpc_service import TradingGrpcService
from app.utils.exceptions import DataServiceException, TradingServiceException, handle_xtquant_exception
from generated import common_pb2, health_pb2, trading_pb2
from tests.conftest import GrpcTestContext, RestTestContext


REST_HEALTH_ENDPOINTS = {"/", "/health/", "/health/ready", "/health/live"}
GRPC_HEALTH_METHODS = {"Check"}


@pytest.mark.parametrize("path", ["/", "/health/", "/health/ready", "/health/live"])
def test_rest_health_endpoints(rest_test_context: RestTestContext, path: str):
    response = rest_test_context.client.get(path)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True


def test_liveness_includes_heartbeat_fields(rest_test_context: RestTestContext):
    response = rest_test_context.client.get("/health/live")
    assert response.status_code == 200, response.text
    payload = response.json()
    data = payload["data"]
    assert data["status"] == "alive"
    assert isinstance(data["pid"], int)
    assert data["pid"] > 0
    assert isinstance(data["started_at_ms"], int)
    assert isinstance(data["last_heartbeat_ms"], int)
    assert isinstance(data["uptime_seconds"], (int, float))
    assert isinstance(data["heartbeat_age_seconds"], (int, float))
    assert data["heartbeat_age_seconds"] >= 0


def test_health_includes_qmt_status(rest_test_context: RestTestContext):
    response = rest_test_context.client.get("/health/")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["qmt"]["status"] == "mock"
    assert payload["data"]["qmt"]["xtdata"]["status"] == "mock"
    assert payload["data"]["qmt"]["xttrader"]["status"] == "mock"


def test_readiness_includes_qmt_checks(rest_test_context: RestTestContext):
    response = rest_test_context.client.get("/health/ready")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"]["status"] == "ready"
    assert payload["data"]["checks"]["qmt"]["status"] == "mock"
    assert payload["data"]["checks"]["qmt"]["xtdata"]["status"] == "mock"


def test_readiness_returns_503_when_xtdata_not_connected():
    import importlib

    import app.config as config_module
    import app.main as main_module
    from app.config import Settings, reset_settings
    from app.dependencies import get_xtdata_gateway, reset_services
    from fastapi.testclient import TestClient

    class DisconnectedGateway:
        def get_readiness_snapshot(self) -> dict[str, str | bool | None]:
            return {"status": "disconnected", "ready": False, "reason": "not connected"}

    reset_services()
    reset_settings()
    config_module._settings_instance = Settings(
        app={"debug": True},
        xtquant={"mode": "dev", "data": {}},
        security={"api_keys": []},
    )
    reloaded = importlib.reload(main_module)
    reloaded.app.dependency_overrides[get_xtdata_gateway] = lambda: DisconnectedGateway()
    client = TestClient(reloaded.app)

    try:
        response = client.get("/health/ready")

        assert response.status_code == 503, response.text
        payload = response.json()
        assert payload["success"] is False
        assert payload["data"]["status"] == "not_ready"
        assert payload["data"]["checks"]["qmt"]["ready"] is False
        assert payload["data"]["checks"]["qmt"]["xtdata"]["ready"] is False
    finally:
        reloaded.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_general_exception_handler_masks_details_when_debug_disabled(monkeypatch):
    from starlette.requests import Request

    import app.main as main_module
    from app.config import Settings

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(app={"debug": False}),
    )
    request = Request({"type": "http", "method": "GET", "path": "/boom", "headers": []})

    response = await main_module.general_exception_handler(request, RuntimeError("secret-detail"))

    assert response.status_code == 500
    body = response.body.decode()
    assert "secret-detail" not in body
    assert "Internal server error" in body


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("get", "/api/v1/data/sectors", None),
        ("post", "/api/v1/trading/sessions", {"account_id": "demo-account", "account_type": "STOCK"}),
    ],
)
def test_rest_requires_bearer_token(rest_test_context: RestTestContext, method: str, path: str, json_body):
    request = getattr(rest_test_context.client, method)

    if json_body is None:
        response = request(path)
    else:
        response = request(path, json=json_body)
    assert response.status_code == 401, response.text

    if json_body is None:
        invalid = request(path, headers={"Authorization": "Bearer wrong-token"})
    else:
        invalid = request(path, json=json_body, headers={"Authorization": "Bearer wrong-token"})
    assert invalid.status_code == 401, invalid.text


def test_grpc_health_check_is_exempt_from_auth(grpc_test_context: GrpcTestContext):
    response = grpc_test_context.health_stub.Check(health_pb2.HealthCheckRequest())
    assert response.status == health_pb2.HealthCheckResponse.SERVING


def test_grpc_unary_requires_bearer_token(grpc_test_context: GrpcTestContext):
    with pytest.raises(grpc.RpcError) as exc:
        grpc_test_context.trading_stub.OpenSession(
            trading_pb2.OpenSessionRequest(
                account_id="demo-account",
                account_type=common_pb2.SECURITY_ACCOUNT_TYPE_STOCK,
            )
        )
    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED


def test_grpc_stream_requires_bearer_token(grpc_test_context: GrpcTestContext):
    with pytest.raises(grpc.RpcError) as exc:
        next(
            grpc_test_context.trading_stub.StreamTradingEvents(
                trading_pb2.StreamTradingEventsRequest(session_id="missing-session")
            )
        )
    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED


def test_http_error_mapping_uses_service_unavailable_for_xtquant_runtime_failures():
    data_error = handle_xtquant_exception(
        DataServiceException("xtdata unavailable", error_code="XTDATA_UNAVAILABLE")
    )
    trading_error = handle_xtquant_exception(
        TradingServiceException("xttrader unavailable", error_code="XTTRADER_UNAVAILABLE")
    )

    assert data_error.status_code == 503
    assert data_error.detail["error_code"] == "XTDATA_UNAVAILABLE"
    assert trading_error.status_code == 503
    assert trading_error.detail["error_code"] == "XTTRADER_UNAVAILABLE"


def test_grpc_error_mapping_uses_unavailable_for_xtquant_runtime_failures():
    data_service = DataGrpcService(market_data_service=object(), reference_data_service=object())
    trading_service = TradingGrpcService(trading_manager=object())

    assert (
        data_service._grpc_status_for_error(
            DataServiceException("xtdata unavailable", error_code="XTDATA_UNAVAILABLE")
        )
        == grpc.StatusCode.UNAVAILABLE
    )
    assert (
        trading_service._grpc_status_for_error(
            TradingServiceException("xttrader unavailable", error_code="XTTRADER_UNAVAILABLE")
        )
        == grpc.StatusCode.UNAVAILABLE
    )
