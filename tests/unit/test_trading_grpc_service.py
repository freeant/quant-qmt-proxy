from __future__ import annotations

import threading

from app.grpc_services.trading_grpc_service import TradingGrpcService
from app.services.contracts import OpenSessionCommand
from generated import common_pb2, trading_pb2


class _FakeContext:
    def __init__(self):
        self.code = None
        self.details = None

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details


class _FakeTradingManager:
    def __init__(self):
        self.thread_name = None

    def open_session(self, command: OpenSessionCommand):
        self.thread_name = threading.current_thread().name
        return {
            "session_id": "session_test",
            "account_id": command.account_id,
            "account_type": command.account_type,
            "mode": "mock",
            "environment": "mock",
            "is_real": False,
            "account_profile": None,
            "account_kind": "mock",
            "orders_enabled": False,
            "opened_at_ms": 1,
        }


def test_grpc_open_session_runs_in_blocking_executor():
    manager = _FakeTradingManager()
    service = TradingGrpcService(manager)
    context = _FakeContext()

    response = service.OpenSession(
        trading_pb2.OpenSessionRequest(
            account_id="8890358071",
            account_type=common_pb2.SECURITY_ACCOUNT_TYPE_STOCK,
        ),
        context,
    )

    assert response.session.session_id == "session_test"
    assert manager.thread_name is not None
    assert manager.thread_name.startswith("blocking")
