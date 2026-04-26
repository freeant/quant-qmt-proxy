import threading
import time

import grpc

from app.config import Settings
from app.dependencies import reset_services
from app.grpc_server import create_grpc_server
from generated import common_pb2, data_pb2, data_pb2_grpc, trading_pb2, trading_pb2_grpc


def build_settings(api_keys=None) -> Settings:
    return Settings(
        app={"host": "127.0.0.1", "port": 18080},
        xtquant={"mode": "mock"},
        security={"api_keys": api_keys or []},
        grpc_host="127.0.0.1",
        grpc_port=0,
    )


def test_proto_enum_values_match_xtquant_contract():
    assert common_pb2.ORDER_SIDE_BUY == 23
    assert common_pb2.ORDER_SIDE_SELL == 24
    assert common_pb2.STOCK_PRICE_TYPE_FIX_PRICE == 11
    assert common_pb2.STOCK_PRICE_TYPE_LATEST_PRICE == 5
    assert common_pb2.STOCK_PRICE_TYPE_MARKET_SZ_FULL_OR_CANCEL == 48


def test_grpc_open_session_and_stream_quote():
    reset_services()
    settings = build_settings()
    server = create_grpc_server(settings)
    server.start()
    port = server._bound_port

    try:
        channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        trading_stub = trading_pb2_grpc.TradingServiceStub(channel)
        data_stub = data_pb2_grpc.DataServiceStub(channel)

        open_response = trading_stub.OpenSession(
            trading_pb2.OpenSessionRequest(
                account_id="grpc-account",
                account_type=common_pb2.SECURITY_ACCOUNT_TYPE_STOCK,
            )
        )
        assert open_response.status.code == 0
        assert open_response.session.session_id
        assert open_response.session.environment == "mock"
        assert open_response.session.account_kind == "mock"
        assert open_response.session.orders_enabled is True

        order_response = trading_stub.SubmitStockOrder(
            trading_pb2.SubmitStockOrderRequest(
                session_id=open_response.session.session_id,
                stock_code="000001.SZ",
                side=common_pb2.ORDER_SIDE_BUY,
                price_type=common_pb2.STOCK_PRICE_TYPE_FIX_PRICE,
                volume=100,
                price=12.3,
            )
        )
        assert order_response.status.code == 0
        assert order_response.order.order_id.startswith("mock_")

        stream = data_stub.StreamQuote(
            data_pb2.QuoteStreamRequest(
                symbols=["000001.SZ"],
                period=common_pb2.QUOTE_PERIOD_TICK,
                adjust_type=common_pb2.ADJUST_TYPE_NONE,
            )
        )
        first_event = next(stream)
        assert first_event.symbol == "000001.SZ"
        assert first_event.HasField("tick")
    finally:
        server.stop(0)
        reset_services()


def test_grpc_stream_trading_events_receives_order_update():
    reset_services()
    settings = build_settings()
    server = create_grpc_server(settings)
    server.start()
    port = server._bound_port

    try:
        channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        trading_stub = trading_pb2_grpc.TradingServiceStub(channel)

        open_response = trading_stub.OpenSession(
            trading_pb2.OpenSessionRequest(
                account_id="grpc-stream-account",
                account_type=common_pb2.SECURITY_ACCOUNT_TYPE_STOCK,
            )
        )
        session_id = open_response.session.session_id
        event_stream = trading_stub.StreamTradingEvents(
            trading_pb2.StreamTradingEventsRequest(session_id=session_id)
        )

        def submit_order() -> None:
            time.sleep(0.05)
            trading_stub.SubmitStockOrder(
                trading_pb2.SubmitStockOrderRequest(
                    session_id=session_id,
                    stock_code="000001.SZ",
                    side=common_pb2.ORDER_SIDE_BUY,
                    price_type=common_pb2.STOCK_PRICE_TYPE_FIX_PRICE,
                    volume=100,
                    price=11.2,
                )
            )

        worker = threading.Thread(target=submit_order, daemon=True)
        worker.start()
        event = next(event_stream)
        worker.join(timeout=1)

        assert event.HasField("order_update")
        assert event.order_update.stock_code == "000001.SZ"
    finally:
        server.stop(0)
        reset_services()


def test_grpc_auth_interceptor_requires_bearer_token():
    reset_services()
    settings = build_settings(api_keys=["secret-token"])
    server = create_grpc_server(settings)
    server.start()
    port = server._bound_port

    try:
        channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        stub = trading_pb2_grpc.TradingServiceStub(channel)

        try:
            stub.OpenSession(
                trading_pb2.OpenSessionRequest(
                    account_id="grpc-account",
                    account_type=common_pb2.SECURITY_ACCOUNT_TYPE_STOCK,
                )
            )
            raise AssertionError("expected unauthenticated error")
        except grpc.RpcError as exc:
            assert exc.code() == grpc.StatusCode.UNAUTHENTICATED

        response = stub.OpenSession(
            trading_pb2.OpenSessionRequest(
                account_id="grpc-account",
                account_type=common_pb2.SECURITY_ACCOUNT_TYPE_STOCK,
            ),
            metadata=(("authorization", "Bearer secret-token"),),
        )
        assert response.status.code == 0
    finally:
        server.stop(0)
        reset_services()

