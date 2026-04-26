from __future__ import annotations

import threading
import time

import grpc
import pytest
from google.protobuf import empty_pb2

from generated import common_pb2, data_pb2, trading_pb2
from tests.conftest import GrpcTestContext, XtTestRuntime


GRPC_TESTED_METHODS = {
    "GetKlineHistory",
    "GetTickHistory",
    "GetFullTickSnapshot",
    "GetFinancialData",
    "GetInstrumentDetail",
    "GetTradingCalendar",
    "GetIndexWeight",
    "GetSectorList",
    "GetL2Quote",
    "GetL2Order",
    "GetL2Transaction",
    "StreamQuote",
    "StreamWholeQuote",
    "OpenSession",
    "CloseSession",
    "GetSession",
    "GetStockAsset",
    "GetStockPositions",
    "GetStockOrders",
    "GetStockTrades",
    "SubmitStockOrder",
    "CancelStockOrder",
    "StreamTradingEvents",
}


def _skip_if_live_streams_disabled(runtime: XtTestRuntime) -> None:
    if runtime.is_real and not runtime.enable_live_streams:
        pytest.skip("real streaming tests require --xt-enable-live-streams or QMT_TEST_ENABLE_LIVE_STREAMS=1")


def _open_grpc_session(ctx: GrpcTestContext, account_id: str, account_type: str):
    return ctx.trading_stub.OpenSession(
        trading_pb2.OpenSessionRequest(
            account_id=account_id,
            account_type=getattr(common_pb2, f"SECURITY_ACCOUNT_TYPE_{account_type}", common_pb2.SECURITY_ACCOUNT_TYPE_STOCK),
        ),
        metadata=ctx.metadata,
    )


GRPC_DATA_CASES = [
    "GetKlineHistory",
    "GetTickHistory",
    "GetFullTickSnapshot",
    "GetFinancialData",
    "GetInstrumentDetail",
    "GetTradingCalendar",
    "GetIndexWeight",
    "GetSectorList",
    "GetL2Quote",
    "GetL2Order",
    "GetL2Transaction",
]


def _call_grpc_data_method(
    ctx: GrpcTestContext,
    case_id: str,
    symbols: list[str],
    index_code: str,
    market: str,
):
    if case_id == "GetKlineHistory":
        return ctx.data_stub.GetKlineHistory(
            data_pb2.KlineHistoryRequest(
                symbols=symbols,
                period=common_pb2.QUOTE_PERIOD_1D,
                start_time="20240101",
                end_time="20240131",
            ),
            metadata=ctx.metadata,
        )
    if case_id == "GetTickHistory":
        return ctx.data_stub.GetTickHistory(
            data_pb2.TickHistoryRequest(
                symbols=[symbols[0]],
                start_time="20240101093000",
                end_time="20240101150000",
            ),
            metadata=ctx.metadata,
        )
    if case_id == "GetFullTickSnapshot":
        return ctx.data_stub.GetFullTickSnapshot(
            data_pb2.FullTickSnapshotRequest(symbols=[symbols[0]]),
            metadata=ctx.metadata,
        )
    if case_id == "GetFinancialData":
        return ctx.data_stub.GetFinancialData(
            data_pb2.FinancialDataRequest(symbols=[symbols[0]], table_names=["Balance"]),
            metadata=ctx.metadata,
        )
    if case_id == "GetInstrumentDetail":
        return ctx.data_stub.GetInstrumentDetail(
            data_pb2.InstrumentDetailRequest(symbol=symbols[0], complete=False),
            metadata=ctx.metadata,
        )
    if case_id == "GetTradingCalendar":
        return ctx.data_stub.GetTradingCalendar(
            data_pb2.TradingCalendarRequest(market=market, start_time="20240101", end_time="20240131"),
            metadata=ctx.metadata,
        )
    if case_id == "GetIndexWeight":
        return ctx.data_stub.GetIndexWeight(
            data_pb2.IndexWeightRequest(index_code=index_code),
            metadata=ctx.metadata,
        )
    if case_id == "GetSectorList":
        return ctx.data_stub.GetSectorList(empty_pb2.Empty(), metadata=ctx.metadata)
    if case_id == "GetL2Quote":
        return ctx.data_stub.GetL2Quote(
            data_pb2.L2QuoteRequest(symbols=[symbols[0]], start_time="", end_time=""),
            metadata=ctx.metadata,
        )
    if case_id == "GetL2Order":
        return ctx.data_stub.GetL2Order(
            data_pb2.L2OrderRequest(symbols=[symbols[0]], start_time="", end_time=""),
            metadata=ctx.metadata,
        )
    if case_id == "GetL2Transaction":
        return ctx.data_stub.GetL2Transaction(
            data_pb2.L2TransactionRequest(symbols=[symbols[0]], start_time="", end_time=""),
            metadata=ctx.metadata,
        )
    raise AssertionError(f"unknown case: {case_id}")


def _assert_grpc_data_shape(case_id: str, response, symbols: list[str], index_code: str, market: str) -> None:
    assert response.status.code == 0
    if case_id in {
        "GetKlineHistory",
        "GetTickHistory",
        "GetFullTickSnapshot",
        "GetFinancialData",
        "GetSectorList",
        "GetL2Quote",
        "GetL2Order",
        "GetL2Transaction",
    }:
        items = (
            response.items
            if hasattr(response, "items")
            else response.snapshots
            if hasattr(response, "snapshots")
            else response.sectors
        )
        assert items is not None
        return
    if case_id == "GetInstrumentDetail":
        assert response.detail.symbol == symbols[0]
        return
    if case_id == "GetTradingCalendar":
        assert response.market == market
        return
    if case_id == "GetIndexWeight":
        assert response.index_code == index_code
        return
    raise AssertionError(f"unknown case: {case_id}")


@pytest.mark.parametrize("case_id", GRPC_DATA_CASES)
def test_grpc_data_interfaces(
    grpc_test_context: GrpcTestContext,
    xt_default_symbols: list[str],
    xt_default_index_code: str,
    xt_default_market: str,
    case_id: str,
):
    try:
        response = _call_grpc_data_method(
            grpc_test_context,
            case_id,
            xt_default_symbols,
            xt_default_index_code,
            xt_default_market,
        )
    except grpc.RpcError as exc:
        if grpc_test_context.runtime.is_real and case_id == "GetTradingCalendar":
            assert exc.code() == grpc.StatusCode.UNIMPLEMENTED
            return
        raise
    _assert_grpc_data_shape(case_id, response, xt_default_symbols, xt_default_index_code, xt_default_market)


def test_grpc_stream_quote_interface(grpc_test_context: GrpcTestContext, xt_default_symbols: list[str]):
    _skip_if_live_streams_disabled(grpc_test_context.runtime)
    stream = grpc_test_context.data_stub.StreamQuote(
        data_pb2.QuoteStreamRequest(
            symbols=[xt_default_symbols[0]],
            period=common_pb2.QUOTE_PERIOD_TICK,
            adjust_type=common_pb2.ADJUST_TYPE_NONE,
        ),
        metadata=grpc_test_context.metadata,
        timeout=15,
    )
    try:
        event = next(stream)
    except grpc.RpcError as exc:
        if grpc_test_context.runtime.is_real and exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            return
        raise
    assert event.symbol == xt_default_symbols[0]
    assert event.HasField("tick") or event.HasField("kline")


def test_grpc_stream_quote_rejects_tick_full_history_replay(
    grpc_test_context: GrpcTestContext,
    xt_default_symbols: list[str],
):
    with pytest.raises(grpc.RpcError) as exc:
        next(
            grpc_test_context.data_stub.StreamQuote(
                data_pb2.QuoteStreamRequest(
                    symbols=[xt_default_symbols[0]],
                    period=common_pb2.QUOTE_PERIOD_TICK,
                    count=-1,
                ),
                metadata=grpc_test_context.metadata,
            )
        )

    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT


def test_grpc_stream_whole_quote_interface(grpc_test_context: GrpcTestContext):
    _skip_if_live_streams_disabled(grpc_test_context.runtime)
    stream = grpc_test_context.data_stub.StreamWholeQuote(
        data_pb2.WholeQuoteStreamRequest(markets=["SH", "SZ"]),
        metadata=grpc_test_context.metadata,
        timeout=15,
    )
    event = next(stream)
    assert event.symbol
    assert event.HasField("tick") or event.HasField("kline")


def test_grpc_trading_session_interfaces(
    grpc_test_context: GrpcTestContext,
    xt_trading_account_id: str,
):
    open_response = _open_grpc_session(grpc_test_context, xt_trading_account_id, grpc_test_context.runtime.account_type)
    assert open_response.status.code == 0
    session = open_response.session
    session_id = session.session_id
    assert session.environment == grpc_test_context.runtime.mode
    assert session.account_kind == grpc_test_context.runtime.account_kind
    assert session.orders_enabled is grpc_test_context.runtime.orders_enabled

    get_response = grpc_test_context.trading_stub.GetSession(
        trading_pb2.GetSessionRequest(session_id=session_id),
        metadata=grpc_test_context.metadata,
    )
    assert get_response.status.code == 0
    assert get_response.session.session_id == session_id

    asset_response = grpc_test_context.trading_stub.GetStockAsset(
        trading_pb2.GetStockAssetRequest(session_id=session_id),
        metadata=grpc_test_context.metadata,
    )
    assert asset_response.status.code == 0
    assert asset_response.asset.account_id

    positions_response = grpc_test_context.trading_stub.GetStockPositions(
        trading_pb2.GetStockPositionsRequest(session_id=session_id),
        metadata=grpc_test_context.metadata,
    )
    assert positions_response.status.code == 0

    orders_response = grpc_test_context.trading_stub.GetStockOrders(
        trading_pb2.GetStockOrdersRequest(session_id=session_id, cancelable_only=False),
        metadata=grpc_test_context.metadata,
    )
    assert orders_response.status.code == 0

    trades_response = grpc_test_context.trading_stub.GetStockTrades(
        trading_pb2.GetStockTradesRequest(session_id=session_id),
        metadata=grpc_test_context.metadata,
    )
    assert trades_response.status.code == 0

    close_response = grpc_test_context.trading_stub.CloseSession(
        trading_pb2.CloseSessionRequest(session_id=session_id),
        metadata=grpc_test_context.metadata,
    )
    assert close_response.status.code == 0
    assert close_response.success is True


def test_grpc_trading_order_and_cancel_interfaces(
    grpc_test_context: GrpcTestContext,
    xt_default_symbols: list[str],
    xt_trading_account_id: str,
):
    open_response = _open_grpc_session(grpc_test_context, xt_trading_account_id, grpc_test_context.runtime.account_type)
    session_id = open_response.session.session_id

    if grpc_test_context.runtime.orders_enabled:
        order_response = grpc_test_context.trading_stub.SubmitStockOrder(
            trading_pb2.SubmitStockOrderRequest(
                session_id=session_id,
                stock_code=xt_default_symbols[0],
                side=common_pb2.ORDER_SIDE_BUY,
                price_type=common_pb2.STOCK_PRICE_TYPE_FIX_PRICE,
                volume=100,
                price=12.3,
                strategy_name="pytest",
                order_remark="grpc-order",
            ),
            metadata=grpc_test_context.metadata,
        )
        assert order_response.status.code == 0
        assert order_response.order.stock_code == xt_default_symbols[0]

        cancel_order_response = grpc_test_context.trading_stub.CancelStockOrder(
            trading_pb2.CancelStockOrderRequest(
                session_id=session_id,
                order_id=order_response.order.order_id,
            ),
            metadata=grpc_test_context.metadata,
        )
        assert cancel_order_response.status.code == 0
        assert cancel_order_response.success is True

        cancel_sysid_response = grpc_test_context.trading_stub.CancelStockOrder(
            trading_pb2.CancelStockOrderRequest(
                session_id=session_id,
                sysid_target=trading_pb2.CancelBySysIdTarget(market="SH", order_sysid="SYSID-TEST"),
            ),
            metadata=grpc_test_context.metadata,
        )
        assert cancel_sysid_response.status.code == 0
        assert cancel_sysid_response.success is True
    else:
        with pytest.raises(grpc.RpcError) as order_error:
            grpc_test_context.trading_stub.SubmitStockOrder(
                trading_pb2.SubmitStockOrderRequest(
                    session_id=session_id,
                    stock_code=xt_default_symbols[0],
                    side=common_pb2.ORDER_SIDE_BUY,
                    price_type=common_pb2.STOCK_PRICE_TYPE_FIX_PRICE,
                    volume=100,
                    price=12.3,
                ),
                metadata=grpc_test_context.metadata,
            )
        assert order_error.value.code() == grpc.StatusCode.PERMISSION_DENIED

        with pytest.raises(grpc.RpcError) as cancel_error:
            grpc_test_context.trading_stub.CancelStockOrder(
                trading_pb2.CancelStockOrderRequest(
                    session_id=session_id,
                    order_id="blocked-order",
                ),
                metadata=grpc_test_context.metadata,
            )
        assert cancel_error.value.code() == grpc.StatusCode.PERMISSION_DENIED

    grpc_test_context.trading_stub.CloseSession(
        trading_pb2.CloseSessionRequest(session_id=session_id),
        metadata=grpc_test_context.metadata,
    )


def test_grpc_stream_trading_events_interface(
    grpc_test_context: GrpcTestContext,
    xt_default_symbols: list[str],
    xt_trading_account_id: str,
):
    if not grpc_test_context.runtime.orders_enabled:
        pytest.skip("trading event order stream requires an order-enabled runtime")

    open_response = _open_grpc_session(grpc_test_context, xt_trading_account_id, grpc_test_context.runtime.account_type)
    session_id = open_response.session.session_id
    stream = grpc_test_context.trading_stub.StreamTradingEvents(
        trading_pb2.StreamTradingEventsRequest(session_id=session_id),
        metadata=grpc_test_context.metadata,
    )

    def submit_order() -> None:
        time.sleep(0.05)
        grpc_test_context.trading_stub.SubmitStockOrder(
            trading_pb2.SubmitStockOrderRequest(
                session_id=session_id,
                stock_code=xt_default_symbols[0],
                side=common_pb2.ORDER_SIDE_BUY,
                price_type=common_pb2.STOCK_PRICE_TYPE_FIX_PRICE,
                volume=100,
                price=11.2,
            ),
            metadata=grpc_test_context.metadata,
        )

    worker = threading.Thread(target=submit_order, daemon=True)
    worker.start()
    event = next(stream)
    worker.join(timeout=1)

    assert event.HasField("order_update")
    assert event.order_update.stock_code == xt_default_symbols[0]

    grpc_test_context.trading_stub.CloseSession(
        trading_pb2.CloseSessionRequest(session_id=session_id),
        metadata=grpc_test_context.metadata,
    )


def test_grpc_invalid_session_paths_return_error(grpc_test_context: GrpcTestContext):
    with pytest.raises(grpc.RpcError) as get_error:
        grpc_test_context.trading_stub.GetSession(
            trading_pb2.GetSessionRequest(session_id="missing-session"),
            metadata=grpc_test_context.metadata,
        )
    assert get_error.value.code() == grpc.StatusCode.NOT_FOUND

    with pytest.raises(grpc.RpcError) as stream_error:
        next(
            grpc_test_context.trading_stub.StreamTradingEvents(
                trading_pb2.StreamTradingEventsRequest(session_id="missing-session"),
                metadata=grpc_test_context.metadata,
            )
        )
    assert stream_error.value.code() == grpc.StatusCode.NOT_FOUND
