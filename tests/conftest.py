from __future__ import annotations

import importlib
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import grpc
import pytest
from fastapi.testclient import TestClient

import app.config as config_module
from app.config import Settings, load_config, reset_settings
from app.dependencies import reset_services
from app.grpc_server import create_grpc_server
from generated import data_pb2_grpc, health_pb2_grpc, trading_pb2_grpc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@dataclass(frozen=True)
class XtTestRuntime:
    mode: str
    local_config_present: bool
    qmt_userdata_path: str | None
    account_profile: str | None
    account_id: str | None
    account_type: str
    account_kind: str
    api_key: str
    enable_live_streams: bool
    enable_prod_tests: bool
    prod_readonly_enabled: bool
    prod_unlock_active: bool
    orders_enabled: bool

    @property
    def is_real(self) -> bool:
        return self.mode in {"dev", "prod"}


@dataclass
class RestTestContext:
    client: TestClient
    headers: dict[str, str]
    runtime: XtTestRuntime


@dataclass
class GrpcTestContext:
    server: grpc.Server
    channel: grpc.Channel
    data_stub: data_pb2_grpc.DataServiceStub
    trading_stub: trading_pb2_grpc.TradingServiceStub
    health_stub: health_pb2_grpc.HealthStub
    metadata: tuple[tuple[str, str], ...] | None
    runtime: XtTestRuntime


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_api_key(mode: str) -> str:
    mapping = {
        "mock": "mock-api-key-001",
        "dev": "dev-api-key-001",
        "prod": "prod-api-key-001",
    }
    return mapping.get(mode, "mock-api-key-001")


def _find_profile(settings: Settings, profile_name: str | None):
    if not profile_name:
        return None
    for profile in settings.xtquant.trading.accounts:
        if profile.name == profile_name:
            return profile
    return None


def pytest_addoption(parser):
    group = parser.getgroup("xtquant")
    group.addoption(
        "--xt-mode",
        action="store",
        default=os.getenv("QMT_TEST_MODE", "mock"),
        choices=["mock", "dev", "prod"],
        help="xtquant runtime mode for tests",
    )
    group.addoption(
        "--xt-account-profile",
        action="store",
        default=os.getenv("QMT_TEST_ACCOUNT_PROFILE"),
        help="named account profile from config.test.local.yml",
    )
    group.addoption(
        "--xt-qmt-userdata-path",
        action="store",
        default=os.getenv("QMT_TEST_QMT_USERDATA_PATH"),
        help="QMT userdata path override for real xtquant tests (broker QMT usually uses userdata, MiniQMT usually uses userdata_mini)",
    )
    group.addoption(
        "--xt-api-key",
        action="store",
        default=os.getenv("QMT_TEST_API_KEY"),
        help="API key injected into REST/gRPC/WebSocket tests",
    )
    group.addoption(
        "--xt-enable-live-streams",
        action="store_true",
        default=_env_flag("QMT_TEST_ENABLE_LIVE_STREAMS", False),
        help="run real xtdata streaming tests that depend on live market pushes",
    )
    group.addoption(
        "--xt-enable-prod-tests",
        action="store_true",
        default=_env_flag("QMT_TEST_ENABLE_PROD_TESTS", False),
        help="unlock readonly prod interface tests when config and token checks also pass",
    )


@pytest.fixture(scope="session", autouse=True)
def configure_global_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("tests/test_results.log"),
        ],
    )
    yield


@pytest.fixture(scope="session")
def xt_test_runtime(pytestconfig) -> XtTestRuntime:
    mode = pytestconfig.getoption("--xt-mode")
    local_config_present = Path("config.test.local.yml").exists()
    base_settings = load_config("config.yml", app_mode=mode, local_config_file="config.test.local.yml")

    account_profile = (
        pytestconfig.getoption("--xt-account-profile")
        or base_settings.testing.default_account_profile
    )
    qmt_userdata_path = (
        pytestconfig.getoption("--xt-qmt-userdata-path")
        or base_settings.testing.qmt_userdata_path
        or base_settings.xtquant.data.qmt_userdata_path
    )
    api_key = pytestconfig.getoption("--xt-api-key") or _default_api_key(mode)
    enable_live_streams = pytestconfig.getoption("--xt-enable-live-streams")
    enable_prod_tests = pytestconfig.getoption("--xt-enable-prod-tests")

    if mode == "mock":
        return XtTestRuntime(
            mode=mode,
            local_config_present=local_config_present,
            qmt_userdata_path=None,
            account_profile=None,
            account_id="mock-account-001",
            account_type="STOCK",
            account_kind="mock",
            api_key=api_key,
            enable_live_streams=enable_live_streams,
            enable_prod_tests=enable_prod_tests,
            prod_readonly_enabled=False,
            prod_unlock_active=False,
            orders_enabled=True,
        )

    if not local_config_present:
        pytest.skip("real xtquant tests require config.test.local.yml")
    if not qmt_userdata_path:
        pytest.skip("real xtquant tests require qmt_userdata_path in config.test.local.yml or --xt-qmt-userdata-path")

    profile = _find_profile(base_settings, account_profile)
    if profile is None:
        raise pytest.UsageError("real xtquant tests require --xt-account-profile or testing.default_account_profile")

    if not profile.enabled:
        raise pytest.UsageError(f"account profile '{profile.name}' is disabled")
    if mode not in {allowed.value for allowed in profile.allowed_modes}:
        raise pytest.UsageError(f"account profile '{profile.name}' is not allowed in mode={mode}")
    if mode == "dev" and profile.account_kind.value != "simulated":
        raise pytest.UsageError("dev tests require a simulated account profile")
    if mode == "prod" and profile.account_kind.value != "real":
        raise pytest.UsageError("prod tests require a real account profile")

    prod_unlock_token = os.getenv("QMT_TEST_PROD_UNLOCK_TOKEN")
    prod_unlock_active = bool(
        base_settings.testing.prod_unlock_token
        and prod_unlock_token
        and prod_unlock_token == base_settings.testing.prod_unlock_token
    )
    prod_readonly_enabled = bool(base_settings.testing.enable_prod_readonly_tests)

    if mode == "prod" and not (prod_readonly_enabled and enable_prod_tests and prod_unlock_active):
        pytest.skip(
            "prod tests require config.test.local.yml readonly unlock, --xt-enable-prod-tests, "
            "and matching QMT_TEST_PROD_UNLOCK_TOKEN"
        )

    return XtTestRuntime(
        mode=mode,
        local_config_present=local_config_present,
        qmt_userdata_path=qmt_userdata_path,
        account_profile=profile.name,
        account_id=profile.account_id,
        account_type=profile.account_type,
        account_kind=profile.account_kind.value,
        api_key=api_key,
        enable_live_streams=enable_live_streams,
        enable_prod_tests=enable_prod_tests,
        prod_readonly_enabled=prod_readonly_enabled,
        prod_unlock_active=prod_unlock_active,
        orders_enabled=(mode == "dev" and profile.account_kind.value == "simulated"),
    )


@pytest.fixture(scope="session")
def xt_trading_account_id(xt_test_runtime: XtTestRuntime) -> str:
    return xt_test_runtime.account_id or "mock-account-001"


@pytest.fixture(scope="session")
def xt_default_symbols() -> list[str]:
    return ["000001.SZ", "600000.SH"]


@pytest.fixture(scope="session")
def xt_default_index_code() -> str:
    return "000300.SH"


@pytest.fixture(scope="session")
def xt_default_market() -> str:
    return "SH"


def build_test_settings(
    runtime: XtTestRuntime,
    *,
    app_port: int = 18080,
    grpc_port: int = 0,
) -> Settings:
    accounts: list[dict[str, object]] = []
    if runtime.is_real and runtime.account_id and runtime.account_profile:
        accounts = [
            {
                "name": runtime.account_profile,
                "account_id": runtime.account_id,
                "account_type": runtime.account_type,
                "account_kind": runtime.account_kind,
                "allowed_modes": [runtime.mode],
                "enabled": True,
            }
        ]

    return Settings(
        app={"host": "127.0.0.1", "port": app_port, "debug": False},
        xtquant={
            "mode": runtime.mode,
            "data": {
                "qmt_userdata_path": runtime.qmt_userdata_path,
                "max_queue_size": 1000,
                "max_subscriptions": 100,
                "heartbeat_interval": 60,
                "whole_quote_enabled": True,
            },
            "trading": {"accounts": accounts, "enable_prod_orders": False},
        },
        testing={
            "default_account_profile": runtime.account_profile,
            "enable_prod_readonly_tests": runtime.prod_readonly_enabled,
            "qmt_userdata_path": runtime.qmt_userdata_path,
            "prod_unlock_token": "configured" if runtime.prod_unlock_active else None,
        },
        security={"api_keys": [runtime.api_key] if runtime.api_key else []},
        grpc_host="127.0.0.1",
        grpc_port=grpc_port,
        app_servers="all",
    )


@pytest.fixture
def grpc_test_context(xt_test_runtime: XtTestRuntime) -> Iterator[GrpcTestContext]:
    reset_services()
    settings = build_test_settings(xt_test_runtime, grpc_port=0)
    server = create_grpc_server(settings)
    server.start()
    port = server._bound_port
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    metadata = (("authorization", f"Bearer {xt_test_runtime.api_key}"),) if xt_test_runtime.api_key else None
    try:
        yield GrpcTestContext(
            server=server,
            channel=channel,
            data_stub=data_pb2_grpc.DataServiceStub(channel),
            trading_stub=trading_pb2_grpc.TradingServiceStub(channel),
            health_stub=health_pb2_grpc.HealthStub(channel),
            metadata=metadata,
            runtime=xt_test_runtime,
        )
    finally:
        channel.close()
        server.stop(0)
        reset_services()


@pytest.fixture
def rest_test_context(xt_test_runtime: XtTestRuntime) -> Iterator[RestTestContext]:
    reset_services()
    reset_settings()
    settings = build_test_settings(xt_test_runtime)
    config_module._settings_instance = settings

    import app.main as main_module

    main_module = importlib.reload(main_module)
    headers = {"Authorization": f"Bearer {xt_test_runtime.api_key}"} if xt_test_runtime.api_key else {}
    with TestClient(main_module.app) as client:
        yield RestTestContext(client=client, headers=headers, runtime=xt_test_runtime)

    main_module.app.dependency_overrides.clear()
    reset_services()
    reset_settings()


def pytest_configure(config):
    config.addinivalue_line("markers", "rest: REST API tests")
    config.addinivalue_line("markers", "grpc: gRPC tests")
    config.addinivalue_line("markers", "integration: integration tests requiring external services")
    config.addinivalue_line("markers", "performance: performance tests")
    config.addinivalue_line("markers", "slow: slow tests")
    config.addinivalue_line("markers", "future: future-facing tests")


def pytest_collection_modifyitems(config, items):
    for item in items:
        path = str(item.fspath)
        if "rest" in path:
            item.add_marker(pytest.mark.rest)
        if "grpc" in path:
            item.add_marker(pytest.mark.grpc)


def pytest_report_header(config):
    return [
        "QMT Proxy test runtime",
        "=" * 80,
        f"test mode={config.getoption('--xt-mode')}",
        "Python version: " + sys.version.split()[0],
    ]


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        logger = logging.getLogger(__name__)
        logger.error(f"test failed: {item.nodeid}")
        if hasattr(rep, "longrepr"):
            logger.error(f"error: {str(rep.longrepr)[:400]}")
