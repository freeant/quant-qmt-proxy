from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from app.config import AccountKind, XTQuantMode, load_config
from app.utils.exceptions import ConfigurationException
from app.grpc_server import RequestLoggingServerInterceptor, create_grpc_server
from generated import trading_pb2
from app.utils import logger as logger_module
from tests.conftest import XtTestRuntime, build_test_settings


def test_load_config_merges_runtime_local_settings_accounts_and_subscription_settings(tmp_path: Path, monkeypatch):
    base_file = tmp_path / "config.yml"
    local_file = tmp_path / "config.local.yml"

    base_file.write_text(
        yaml.safe_dump(
            {
                "app": {"name": "xtquant-proxy", "version": "1.0.0"},
                "logging": {"file": "logs/app.log", "error_file": "logs/error.log"},
                "grpc": {"host": "0.0.0.0", "port": 50051},
                "xtquant": {
                    "qmt_userdata_path": "C:/base/qmt",
                    "data": {
                        "max_queue_size": 1000,
                        "max_subscriptions": 100,
                        "heartbeat_timeout": 60,
                        "whole_quote_enabled": False,
                    },
                    "trading": {
                        "enable_prod_orders": False,
                        "accounts": [
                            {
                                "name": "sim-base",
                                "account_id": "SIM-001",
                                "account_type": "STOCK",
                                "account_kind": "simulated",
                                "allowed_modes": ["dev"],
                                "enabled": True,
                            }
                        ],
                    },
                },
                "testing": {
                    "default_account_profile": "sim-base",
                    "enable_prod_readonly_tests": False,
                },
                "modes": {
                    "mock": {"xtquant_mode": "mock", "api_keys": ["mock-api-key-001"]},
                    "dev": {"xtquant_mode": "dev", "api_keys": ["dev-api-key-001"]},
                    "prod": {"xtquant_mode": "prod", "api_keys": ["prod-api-key-001"]},
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    local_file.write_text(
        yaml.safe_dump(
            {
                "xtquant": {
                    "qmt_userdata_path": "D:/local/qmt",
                    "trading": {
                        "enable_prod_orders": True,
                        "accounts": [
                            {
                                "name": "sim-local",
                                "account_id": "SIM-LOCAL",
                                "account_type": "STOCK",
                                "account_kind": "simulated",
                                "allowed_modes": ["dev"],
                                "enabled": True,
                            },
                            {
                                "name": "prod-local",
                                "account_id": "PROD-LOCAL",
                                "account_type": "STOCK",
                                "account_kind": "real",
                                "allowed_modes": ["prod"],
                                "enabled": True,
                            },
                        ]
                    },
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("APP_MODE", "prod")
    monkeypatch.setenv("APP_SERVERS", "grpc")
    monkeypatch.setenv("APP_HOST", "127.0.0.1")
    monkeypatch.setenv("APP_PORT", "18080")
    monkeypatch.setenv("GRPC_PORT", "19090")
    monkeypatch.setenv("APP_API_KEYS", "pytest-key-1,pytest-key-2")

    settings = load_config(str(base_file), app_mode="prod", local_config_file=str(local_file))

    assert settings.xtquant.mode == XTQuantMode.PROD
    assert settings.xtquant.data.max_queue_size == 1000
    assert settings.xtquant.data.max_subscriptions == 100
    assert settings.xtquant.data.heartbeat_interval == 60
    assert settings.xtquant.data.whole_quote_enabled is False
    assert settings.app_servers == "grpc"
    assert settings.app.host == "127.0.0.1"
    assert settings.app.port == 18080
    assert settings.grpc_port == 19090
    assert settings.xtquant.data.qmt_userdata_path == "D:/local/qmt"
    assert settings.xtquant.trading.enable_prod_orders is True
    assert settings.security.api_keys == ["pytest-key-1", "pytest-key-2"]
    assert settings.testing.default_account_profile == "sim-base"
    assert settings.testing.enable_prod_readonly_tests is False
    assert len(settings.xtquant.trading.accounts) == 2
    assert settings.xtquant.trading.accounts[0].account_kind == AccountKind.SIMULATED
    assert settings.xtquant.trading.accounts[1].account_kind == AccountKind.REAL


def test_load_config_keeps_test_local_settings_out_of_runtime_xtdata_path(tmp_path: Path):
    base_file = tmp_path / "config.yml"
    local_file = tmp_path / "config.test.local.yml"

    base_file.write_text(
        yaml.safe_dump(
            {
                "xtquant": {
                    "qmt_userdata_path": "C:/runtime/qmt",
                    "trading": {"accounts": []},
                },
                "testing": {
                    "default_account_profile": None,
                    "enable_prod_readonly_tests": False,
                },
                "modes": {
                    "dev": {"xtquant_mode": "dev", "api_keys": ["dev-api-key-001"]},
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    local_file.write_text(
        yaml.safe_dump(
            {
                "testing": {
                    "default_account_profile": "sim-local",
                    "enable_prod_readonly_tests": True,
                    "prod_unlock_token": "token-123",
                    "qmt_userdata_path": "D:/test-only/qmt",
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    settings = load_config(str(base_file), app_mode="dev", local_config_file=str(local_file))

    assert settings.xtquant.data.qmt_userdata_path == "C:/runtime/qmt"
    assert settings.testing.default_account_profile == "sim-local"
    assert settings.testing.enable_prod_readonly_tests is True
    assert settings.testing.prod_unlock_token == "token-123"
    assert settings.testing.qmt_userdata_path == "D:/test-only/qmt"


def test_load_config_fails_fast_when_configuration_file_is_empty(tmp_path: Path):
    config_file = tmp_path / "empty.yml"
    config_file.write_text("", encoding="utf-8")

    with pytest.raises(ConfigurationException) as exc:
        load_config(str(config_file), app_mode="dev", local_config_file=None)

    assert exc.value.error_code == "CONFIG_FILE_MISSING"


def test_load_config_fails_fast_when_requested_mode_is_missing(tmp_path: Path):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "xtquant": {"qmt_userdata_path": "C:/runtime/qmt"},
                "modes": {
                    "mock": {"xtquant_mode": "mock", "api_keys": ["mock-api-key-001"]},
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationException) as exc:
        load_config(str(config_file), app_mode="prod", local_config_file=None)

    assert exc.value.error_code == "MODE_CONFIG_MISSING"


def test_load_config_fails_fast_when_app_mode_is_invalid(tmp_path: Path):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "xtquant": {"qmt_userdata_path": "C:/runtime/qmt"},
                "modes": {
                    "dev": {"xtquant_mode": "dev", "api_keys": ["dev-api-key-001"]},
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationException) as exc:
        load_config(str(config_file), app_mode="production", local_config_file=None)

    assert exc.value.error_code == "INVALID_APP_MODE"


def test_load_config_fails_fast_when_app_servers_is_invalid(tmp_path: Path, monkeypatch):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "xtquant": {"qmt_userdata_path": "C:/runtime/qmt"},
                "modes": {
                    "dev": {"xtquant_mode": "dev", "api_keys": ["dev-api-key-001"]},
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("APP_SERVERS", "grpcx")

    with pytest.raises(ConfigurationException) as exc:
        load_config(str(config_file), app_mode="dev", local_config_file=None)

    assert exc.value.error_code == "INVALID_APP_SERVERS"


def test_load_config_defaults_to_mock_without_app_mode(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)
    settings = load_config("config.yml", local_config_file=None)
    assert settings.xtquant.mode == XTQuantMode.MOCK


def test_load_config_uses_mode_debug_when_app_debug_unset(monkeypatch):
    monkeypatch.delenv("APP_DEBUG", raising=False)
    settings = load_config("config.yml", app_mode="mock", local_config_file=None)
    assert settings.app.debug is True


def test_load_config_honors_app_debug_override(monkeypatch):
    monkeypatch.setenv("APP_DEBUG", "false")
    settings = load_config("config.yml", app_mode="mock", local_config_file=None)
    assert settings.app.debug is False


def test_start_py_does_not_force_app_debug_without_reload(monkeypatch):
    import run
    import start

    monkeypatch.delenv("APP_DEBUG", raising=False)
    monkeypatch.setattr(
        start.argparse.ArgumentParser,
        "parse_args",
        lambda self: start.argparse.Namespace(
            mode="mock",
            servers="all",
            host=None,
            port=None,
            grpc_host=None,
            grpc_port=None,
            reload=False,
        ),
    )
    monkeypatch.setattr(run, "main", lambda: None)

    start.main()

    assert os.getenv("APP_DEBUG") is None


def test_configure_logging_is_idempotent(tmp_path: Path):
    log_file = tmp_path / "app.log"
    error_file = tmp_path / "error.log"

    logger_module.configure_logging(
        log_file=str(log_file),
        error_log_file=str(error_file),
        console_output=False,
    )
    first_sink_ids = list(logger_module._configured_sink_ids)

    logger_module.configure_logging(
        log_file=str(log_file),
        error_log_file=str(error_file),
        console_output=False,
    )

    assert logger_module._configured_sink_ids == first_sink_ids
    logger_module.logger.info("test-log")
    assert log_file.exists()


def test_create_grpc_server_fails_when_port_bind_returns_zero(monkeypatch):
    class FakeServer:
        def add_insecure_port(self, address: str) -> int:
            return 0

    fake_server = FakeServer()

    monkeypatch.setattr("app.grpc_server.grpc.server", lambda *args, **kwargs: fake_server)
    monkeypatch.setattr("app.grpc_server.data_pb2_grpc.add_DataServiceServicer_to_server", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.grpc_server.trading_pb2_grpc.add_TradingServiceServicer_to_server", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.grpc_server.health_pb2_grpc.add_HealthServicer_to_server", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.grpc_server.get_market_data_service", lambda settings: object())
    monkeypatch.setattr("app.grpc_server.get_reference_data_service", lambda settings: object())
    monkeypatch.setattr("app.grpc_server.get_trading_session_manager", lambda settings: object())

    with pytest.raises(RuntimeError, match="failed to bind gRPC server"):
        create_grpc_server()


def test_build_test_settings_keeps_prod_automation_readonly():
    runtime = XtTestRuntime(
        mode="prod",
        local_config_present=True,
        qmt_userdata_path="D:/QMT/userdata",
        account_profile="prod-main",
        account_id="PROD-001",
        account_type="STOCK",
        account_kind="real",
        api_key="prod-api-key-001",
        enable_live_streams=False,
        enable_prod_tests=True,
        prod_readonly_enabled=True,
        prod_unlock_active=True,
        orders_enabled=False,
    )

    settings = build_test_settings(runtime)

    assert settings.xtquant.mode == XTQuantMode.PROD
    assert settings.xtquant.trading.enable_prod_orders is False


def test_log_runtime_configuration_contains_core_diagnostics(monkeypatch):
    runtime = XtTestRuntime(
        mode="dev",
        local_config_present=True,
        qmt_userdata_path="C:/BrokerQMT/userdata",
        account_profile="sim-dev",
        account_id="SIM-001",
        account_type="STOCK",
        account_kind="simulated",
        api_key="dev-api-key-001",
        enable_live_streams=False,
        enable_prod_tests=False,
        prod_readonly_enabled=False,
        prod_unlock_active=False,
        orders_enabled=True,
    )
    settings = build_test_settings(runtime, app_port=18080, grpc_port=19090)
    messages: list[str] = []

    monkeypatch.setattr(logger_module.logger, "info", lambda message: messages.append(message))

    logger_module.log_runtime_configuration("rest", settings)

    assert messages
    message = messages[-1]
    assert "surface=rest" in message
    assert "mode=dev" in message
    assert "servers=all" in message
    assert "qmt_userdata_path=C:/BrokerQMT/userdata" in message
    assert "enable_prod_orders=False" in message
    assert "account_profiles=1" in message
    assert "api_key_enabled=True" in message


def test_grpc_request_summary_includes_cancel_target_details():
    request = trading_pb2.CancelStockOrderRequest(
        session_id="session-001",
        sysid_target=trading_pb2.CancelBySysIdTarget(market="SH", order_sysid="SYSID-001"),
    )

    summary = RequestLoggingServerInterceptor._request_summary(request)

    assert "session_id=session-001" in summary
    assert "sysid_market=SH" in summary
    assert "sysid_order_sysid=SYSID-001" in summary


def test_run_main_logs_actual_bound_grpc_port(monkeypatch):
    import run as run_module

    settings = build_test_settings(
        XtTestRuntime(
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
        ),
        grpc_port=50051,
    )
    settings.app_servers = "all"
    messages: list[str] = []
    fake_server = type(
        "FakeServer",
        (),
        {
            "_bound_port": 19091,
            "start": lambda self: None,
            "stop": lambda self, grace=0: None,
        },
    )()

    monkeypatch.setattr(run_module, "get_settings", lambda: settings)
    monkeypatch.setattr(run_module, "configure_logging_from_settings", lambda settings: None)
    monkeypatch.setattr(run_module, "print_banner", lambda settings: None)
    monkeypatch.setattr(run_module, "create_grpc_server", lambda settings: fake_server)
    monkeypatch.setattr(run_module, "run_rest_server", lambda settings, reload_enabled=None: None)
    monkeypatch.setattr(run_module.logger, "info", lambda message: messages.append(message))
    monkeypatch.setattr(run_module.logger, "warning", lambda message: messages.append(message))

    run_module.main()

    assert any("gRPC server started on 127.0.0.1:19091" in message for message in messages)
