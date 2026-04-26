from __future__ import annotations

import importlib

from fastapi.routing import APIRoute
from starlette.routing import WebSocketRoute

import app.config as config_module
from app.config import reset_settings
from app.dependencies import reset_services
from app.grpc_services.data_grpc_service import DataGrpcService
from app.grpc_services.health_grpc_service import HealthGrpcService
from app.grpc_services.trading_grpc_service import TradingGrpcService
from tests.conftest import build_test_settings, XtTestRuntime
from tests.unit.test_grpc_api_interfaces import GRPC_TESTED_METHODS
from tests.unit.test_health_and_auth import GRPC_HEALTH_METHODS, REST_HEALTH_ENDPOINTS
from tests.unit.test_rest_api_interfaces import REST_TESTED_ENDPOINTS
from tests.unit.test_rest_websocket import WEBSOCKET_TESTED_ENDPOINTS


def _build_mock_runtime() -> XtTestRuntime:
    return XtTestRuntime(
        mode="mock",
        local_config_present=False,
        qmt_userdata_path=None,
        account_profile=None,
        account_id="mock-account-001",
        account_type="STOCK",
        account_kind="mock",
        api_key="mock-api-key-001",
        enable_live_streams=False,
        enable_prod_tests=False,
        prod_readonly_enabled=False,
        prod_unlock_active=False,
        orders_enabled=True,
    )


def test_fastapi_routes_have_matching_tests():
    reset_services()
    reset_settings()
    config_module._settings_instance = build_test_settings(_build_mock_runtime())

    import app.main as main_module

    main_module = importlib.reload(main_module)
    actual_http_paths = {
        route.path
        for route in main_module.app.routes
        if isinstance(route, APIRoute) and (route.path == "/" or route.path.startswith("/health") or route.path.startswith("/api/v1/"))
    }
    actual_ws_paths = {
        route.path
        for route in main_module.app.routes
        if isinstance(route, WebSocketRoute) and route.path.startswith("/ws/")
    }
    tested_http_paths = REST_HEALTH_ENDPOINTS | REST_TESTED_ENDPOINTS

    assert actual_http_paths <= tested_http_paths
    assert actual_ws_paths <= WEBSOCKET_TESTED_ENDPOINTS


def test_grpc_servicer_methods_have_matching_tests():
    actual_methods = {
        name
        for service in (DataGrpcService, TradingGrpcService, HealthGrpcService)
        for name in dir(service)
        if name[:1].isupper() and callable(getattr(service, name))
    }
    tested_methods = GRPC_TESTED_METHODS | GRPC_HEALTH_METHODS

    assert actual_methods <= tested_methods

