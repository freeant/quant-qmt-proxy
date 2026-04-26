from __future__ import annotations

import grpc
from google.protobuf import empty_pb2

from generated import common_pb2, data_pb2, data_pb2_grpc, health_pb2, health_pb2_grpc, trading_pb2, trading_pb2_grpc


class QMTGrpcClient:
    def __init__(self, host: str = "localhost", port: int = 50051, api_key: str | None = None):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.data_stub = data_pb2_grpc.DataServiceStub(self.channel)
        self.trading_stub = trading_pb2_grpc.TradingServiceStub(self.channel)
        self.health_stub = health_pb2_grpc.HealthStub(self.channel)

    def _metadata(self):
        if not self.api_key:
            return None
        return (("authorization", f"Bearer {self.api_key}"),)

    def check_health(self, service: str = ""):
        return self.health_stub.Check(health_pb2.HealthCheckRequest(service=service), metadata=self._metadata())

    def open_session(self, account_id: str, account_type: int = common_pb2.SECURITY_ACCOUNT_TYPE_STOCK):
        return self.trading_stub.OpenSession(
            trading_pb2.OpenSessionRequest(account_id=account_id, account_type=account_type),
            metadata=self._metadata(),
        )

    def close_session(self, session_id: str):
        return self.trading_stub.CloseSession(
            trading_pb2.CloseSessionRequest(session_id=session_id),
            metadata=self._metadata(),
        )

    def get_stock_asset(self, session_id: str):
        return self.trading_stub.GetStockAsset(
            trading_pb2.GetStockAssetRequest(session_id=session_id),
            metadata=self._metadata(),
        )

    def get_stock_positions(self, session_id: str):
        return self.trading_stub.GetStockPositions(
            trading_pb2.GetStockPositionsRequest(session_id=session_id),
            metadata=self._metadata(),
        )

    def get_stock_orders(self, session_id: str, cancelable_only: bool = False):
        return self.trading_stub.GetStockOrders(
            trading_pb2.GetStockOrdersRequest(session_id=session_id, cancelable_only=cancelable_only),
            metadata=self._metadata(),
        )

    def get_stock_trades(self, session_id: str):
        return self.trading_stub.GetStockTrades(
            trading_pb2.GetStockTradesRequest(session_id=session_id),
            metadata=self._metadata(),
        )

    def submit_stock_order(
        self,
        session_id: str,
        stock_code: str,
        side: int,
        price_type: int,
        volume: int,
        price: float = 0.0,
        strategy_name: str = "",
        order_remark: str = "",
    ):
        return self.trading_stub.SubmitStockOrder(
            trading_pb2.SubmitStockOrderRequest(
                session_id=session_id,
                stock_code=stock_code,
                side=side,
                price_type=price_type,
                volume=volume,
                price=price,
                strategy_name=strategy_name,
                order_remark=order_remark,
            ),
            metadata=self._metadata(),
        )

    def cancel_stock_order(self, session_id: str, order_id: str | None = None, market: str | None = None, order_sysid: str | None = None):
        if order_id:
            request = trading_pb2.CancelStockOrderRequest(session_id=session_id, order_id=order_id)
        else:
            request = trading_pb2.CancelStockOrderRequest(
                session_id=session_id,
                sysid_target=trading_pb2.CancelBySysIdTarget(market=market or "", order_sysid=order_sysid or ""),
            )
        return self.trading_stub.CancelStockOrder(request, metadata=self._metadata())

    def stream_trading_events(self, session_id: str):
        return self.trading_stub.StreamTradingEvents(
            trading_pb2.StreamTradingEventsRequest(session_id=session_id),
            metadata=self._metadata(),
        )

    def get_kline_history(
        self,
        symbols: list[str],
        period: int = common_pb2.QUOTE_PERIOD_1D,
        start_time: str = "",
        end_time: str = "",
        fields: list[str] | None = None,
        adjust_type: int = common_pb2.ADJUST_TYPE_NONE,
        fill_data: bool = True,
    ):
        return self.data_stub.GetKlineHistory(
            data_pb2.KlineHistoryRequest(
                symbols=symbols,
                period=period,
                start_time=start_time,
                end_time=end_time,
                fields=fields or [],
                adjust_type=adjust_type,
                fill_data=fill_data,
            ),
            metadata=self._metadata(),
        )

    def get_tick_history(self, symbols: list[str], start_time: str = "", end_time: str = "", fields: list[str] | None = None):
        return self.data_stub.GetTickHistory(
            data_pb2.TickHistoryRequest(symbols=symbols, start_time=start_time, end_time=end_time, fields=fields or []),
            metadata=self._metadata(),
        )

    def get_full_tick_snapshot(self, symbols: list[str]):
        return self.data_stub.GetFullTickSnapshot(
            data_pb2.FullTickSnapshotRequest(symbols=symbols),
            metadata=self._metadata(),
        )

    def get_sector_list(self):
        return self.data_stub.GetSectorList(empty_pb2.Empty(), metadata=self._metadata())

    def stream_quote(
        self,
        symbols: list[str],
        period: int = common_pb2.QUOTE_PERIOD_TICK,
        start_time: str = "",
        adjust_type: int = common_pb2.ADJUST_TYPE_NONE,
        count: int = 0,
    ):
        return self.data_stub.StreamQuote(
            data_pb2.QuoteStreamRequest(
                symbols=symbols,
                period=period,
                start_time=start_time,
                adjust_type=adjust_type,
                count=count,
            ),
            metadata=self._metadata(),
        )

    def stream_whole_quote(self, markets: list[str] | None = None):
        return self.data_stub.StreamWholeQuote(
            data_pb2.WholeQuoteStreamRequest(markets=markets or ["SH", "SZ"]),
            metadata=self._metadata(),
        )

    def close(self):
        self.channel.close()
