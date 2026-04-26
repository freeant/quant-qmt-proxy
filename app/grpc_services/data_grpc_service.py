from __future__ import annotations

import grpc

from google.protobuf import empty_pb2

from app.services.contracts import FinancialDataQuery, KlineHistoryQuery, L2Query, QuoteSubscriptionSpec, TickHistoryQuery, TradingCalendarQuery, WholeQuoteSubscriptionSpec
from app.services.market_data_service import MarketDataService
from app.services.reference_data_service import ReferenceDataService
from app.utils.exceptions import DataServiceException
from generated import common_pb2, data_pb2, data_pb2_grpc


PERIOD_FROM_PROTO = {
    common_pb2.QUOTE_PERIOD_TICK: "tick",
    common_pb2.QUOTE_PERIOD_1M: "1m",
    common_pb2.QUOTE_PERIOD_5M: "5m",
    common_pb2.QUOTE_PERIOD_15M: "15m",
    common_pb2.QUOTE_PERIOD_30M: "30m",
    common_pb2.QUOTE_PERIOD_1H: "1h",
    common_pb2.QUOTE_PERIOD_1D: "1d",
    common_pb2.QUOTE_PERIOD_1W: "1w",
    common_pb2.QUOTE_PERIOD_1MON: "1mon",
    common_pb2.QUOTE_PERIOD_1Q: "1q",
    common_pb2.QUOTE_PERIOD_1HY: "1hy",
    common_pb2.QUOTE_PERIOD_1Y: "1y",
}

ADJUST_FROM_PROTO = {
    common_pb2.ADJUST_TYPE_UNSPECIFIED: "none",
    common_pb2.ADJUST_TYPE_NONE: "none",
    common_pb2.ADJUST_TYPE_FRONT: "front",
    common_pb2.ADJUST_TYPE_BACK: "back",
    common_pb2.ADJUST_TYPE_FRONT_RATIO: "front_ratio",
    common_pb2.ADJUST_TYPE_BACK_RATIO: "back_ratio",
}


class DataGrpcService(data_pb2_grpc.DataServiceServicer):
    def __init__(self, market_data_service: MarketDataService, reference_data_service: ReferenceDataService):
        self.market_data_service = market_data_service
        self.reference_data_service = reference_data_service

    def GetKlineHistory(self, request, context):
        try:
            items = self.market_data_service.get_kline_history(
                KlineHistoryQuery(
                    symbols=list(request.symbols),
                    period=PERIOD_FROM_PROTO.get(request.period, "1d"),
                    start_time=request.start_time,
                    end_time=request.end_time,
                    fields=list(request.fields),
                    adjust_type=ADJUST_FROM_PROTO.get(request.adjust_type, "none"),
                    fill_data=request.fill_data,
                )
            )
            return data_pb2.KlineHistoryResponse(
                items=[self._to_kline_series(item) for item in items],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.KlineHistoryResponse)

    def GetTickHistory(self, request, context):
        try:
            items = self.market_data_service.get_tick_history(
                TickHistoryQuery(
                    symbols=list(request.symbols),
                    start_time=request.start_time,
                    end_time=request.end_time,
                    fields=list(request.fields),
                    adjust_type=ADJUST_FROM_PROTO.get(request.adjust_type, "none"),
                )
            )
            return data_pb2.TickHistoryResponse(
                items=[self._to_tick_series(item) for item in items],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.TickHistoryResponse)

    def GetFullTickSnapshot(self, request, context):
        try:
            snapshots = self.market_data_service.get_full_tick_snapshot(list(request.symbols))
            return data_pb2.FullTickSnapshotResponse(
                snapshots=[
                    data_pb2.FullTickSnapshot(symbol=item["symbol"], tick=self._to_tick_record(item["tick"]))
                    for item in snapshots
                ],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.FullTickSnapshotResponse)

    def GetFinancialData(self, request, context):
        try:
            items = self.reference_data_service.get_financial_data(
                FinancialDataQuery(
                    symbols=list(request.symbols),
                    table_names=list(request.table_names),
                    start_time=request.start_time,
                    end_time=request.end_time,
                )
            )
            return data_pb2.FinancialDataResponse(
                items=[
                    data_pb2.FinancialTable(
                        symbol=item["symbol"],
                        table_name=item["table_name"],
                        columns=item["columns"],
                        rows=[data_pb2.FinancialDataRow(fields=row) for row in item["rows"]],
                    )
                    for item in items
                ],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.FinancialDataResponse)

    def GetInstrumentDetail(self, request, context):
        try:
            detail = self.reference_data_service.get_instrument_detail(request.symbol, complete=request.complete)
            return data_pb2.InstrumentDetailResponse(
                detail=data_pb2.InstrumentDetail(symbol=detail["symbol"], fields=detail["fields"]),
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.InstrumentDetailResponse)

    def GetTradingCalendar(self, request, context):
        try:
            calendar = self.reference_data_service.get_trading_calendar(
                TradingCalendarQuery(market=request.market, start_time=request.start_time, end_time=request.end_time)
            )
            return data_pb2.TradingCalendarResponse(
                market=calendar["market"],
                dates=calendar["dates"],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.TradingCalendarResponse)

    def GetIndexWeight(self, request, context):
        try:
            weight = self.reference_data_service.get_index_weight(request.index_code)
            return data_pb2.IndexWeightResponse(
                index_code=weight["index_code"],
                components=[
                    data_pb2.IndexComponent(symbol=item["symbol"], weight=item["weight"])
                    for item in weight["components"]
                ],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.IndexWeightResponse)

    def GetSectorList(self, request: empty_pb2.Empty, context):
        try:
            sectors = self.reference_data_service.get_sector_list()
            return data_pb2.SectorListResponse(
                sectors=[data_pb2.SectorInfo(sector_name=item["sector_name"], symbols=item["symbols"]) for item in sectors],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.SectorListResponse)

    def GetL2Quote(self, request, context):
        try:
            items = self.market_data_service.get_l2_quote(L2Query(list(request.symbols), request.start_time, request.end_time))
            return data_pb2.L2QuoteResponse(
                items=[data_pb2.L2Quote(symbol=item["symbol"], quote=self._to_tick_record(item["quote"])) for item in items],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.L2QuoteResponse)

    def GetL2Order(self, request, context):
        try:
            items = self.market_data_service.get_l2_order(L2Query(list(request.symbols), request.start_time, request.end_time))
            return data_pb2.L2OrderResponse(
                items=[
                    data_pb2.L2OrderSeries(
                        symbol=item["symbol"],
                        orders=[self._to_l2_order_record(order) for order in item["orders"]],
                    )
                    for item in items
                ],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.L2OrderResponse)

    def GetL2Transaction(self, request, context):
        try:
            items = self.market_data_service.get_l2_transaction(L2Query(list(request.symbols), request.start_time, request.end_time))
            return data_pb2.L2TransactionResponse(
                items=[
                    data_pb2.L2TransactionSeries(
                        symbol=item["symbol"],
                        transactions=[self._to_l2_transaction_record(tx) for tx in item["transactions"]],
                    )
                    for item in items
                ],
                status=self._status(),
            )
        except DataServiceException as exc:
            return self._error_response(context, self._grpc_status_for_error(exc), exc.message, data_pb2.L2TransactionResponse)

    def StreamQuote(self, request, context):
        try:
            stream = self.market_data_service.stream_quote(
                QuoteSubscriptionSpec(
                    symbols=list(request.symbols),
                    period=PERIOD_FROM_PROTO.get(request.period, "tick"),
                    start_time=request.start_time,
                    adjust_type=ADJUST_FROM_PROTO.get(request.adjust_type, "none"),
                    count=request.count,
                ),
                stop_checker=context.is_active,
            )
            for event in stream:
                yield self._to_quote_event(event)
        except DataServiceException as exc:
            context.set_code(self._grpc_status_for_error(exc))
            context.set_details(exc.message)

    def StreamWholeQuote(self, request, context):
        try:
            stream = self.market_data_service.stream_whole_quote(
                WholeQuoteSubscriptionSpec(markets=list(request.markets) or ["SH", "SZ"]),
                stop_checker=context.is_active,
            )
            for event in stream:
                yield self._to_quote_event(event)
        except DataServiceException as exc:
            context.set_code(self._grpc_status_for_error(exc))
            context.set_details(exc.message)

    def _to_kline_series(self, item: dict):
        return data_pb2.KlineSeries(
            symbol=item["symbol"],
            fields=item["fields"],
            bars=[
                data_pb2.KlineBar(
                    time_ms=bar.get("time_ms", 0),
                    open=bar.get("open", 0.0),
                    high=bar.get("high", 0.0),
                    low=bar.get("low", 0.0),
                    close=bar.get("close", 0.0),
                    volume=bar.get("volume", 0),
                    amount=bar.get("amount", 0.0),
                    settle=bar.get("settle", 0.0),
                    open_interest=bar.get("open_interest", 0),
                    pre_close=bar.get("pre_close", 0.0),
                    suspend_flag=bar.get("suspend_flag", 0),
                )
                for bar in item["bars"]
            ],
        )

    def _to_tick_series(self, item: dict):
        return data_pb2.TickSeries(
            symbol=item["symbol"],
            fields=item["fields"],
            ticks=[self._to_tick_record(tick) for tick in item["ticks"]],
        )

    def _to_tick_record(self, tick: dict):
        return data_pb2.TickRecord(
            time_ms=tick.get("time_ms", 0),
            last_price=tick.get("last_price", 0.0),
            open=tick.get("open", 0.0),
            high=tick.get("high", 0.0),
            low=tick.get("low", 0.0),
            last_close=tick.get("last_close", 0.0),
            amount=tick.get("amount", 0.0),
            volume=tick.get("volume", 0),
            pvolume=tick.get("pvolume", 0),
            open_int=tick.get("open_int", 0),
            stock_status=tick.get("stock_status", 0),
            last_settlement_price=tick.get("last_settlement_price", 0.0),
            ask_price=tick.get("ask_price", []),
            bid_price=tick.get("bid_price", []),
            ask_vol=tick.get("ask_vol", []),
            bid_vol=tick.get("bid_vol", []),
            transaction_num=tick.get("transaction_num", 0),
        )

    def _to_l2_order_record(self, item: dict):
        return data_pb2.L2OrderRecord(
            time_ms=item.get("time_ms", 0),
            price=item.get("price", 0.0),
            volume=item.get("volume", 0),
            entrust_no=item.get("entrust_no", 0),
            entrust_type=item.get("entrust_type", 0),
            entrust_direction=item.get("entrust_direction", 0),
        )

    def _to_l2_transaction_record(self, item: dict):
        return data_pb2.L2TransactionRecord(
            time_ms=item.get("time_ms", 0),
            price=item.get("price", 0.0),
            volume=item.get("volume", 0),
            amount=item.get("amount", 0.0),
            trade_index=item.get("trade_index", 0),
            buy_no=item.get("buy_no", 0),
            sell_no=item.get("sell_no", 0),
            trade_type=item.get("trade_type", 0),
            trade_flag=item.get("trade_flag", 0),
        )

    def _to_quote_event(self, event: dict):
        if event["payload_type"] == "tick":
            return data_pb2.QuoteEvent(
                symbol=event["symbol"],
                period=event["period"],
                event_time_ms=event["event_time_ms"],
                tick=self._to_tick_record(event["data"]),
            )
        data = event["data"]
        return data_pb2.QuoteEvent(
            symbol=event["symbol"],
            period=event["period"],
            event_time_ms=event["event_time_ms"],
            kline=data_pb2.KlineBar(
                time_ms=data.get("time_ms", 0),
                open=data.get("open", 0.0),
                high=data.get("high", 0.0),
                low=data.get("low", 0.0),
                close=data.get("close", 0.0),
                volume=data.get("volume", 0),
                amount=data.get("amount", 0.0),
                settle=data.get("settle", 0.0),
                open_interest=data.get("open_interest", 0),
                pre_close=data.get("pre_close", 0.0),
                suspend_flag=data.get("suspend_flag", 0),
            ),
        )

    def _status(self, code: int = 0, message: str = "success"):
        return common_pb2.Status(code=code, message=message)

    def _grpc_status_for_error(self, exc: DataServiceException) -> grpc.StatusCode:
        if exc.error_code in {"EMPTY_SYMBOLS", "INVALID_SYMBOLS", "INVALID_SUBSCRIPTION_COUNT"}:
            return grpc.StatusCode.INVALID_ARGUMENT
        if exc.error_code == "MAX_SUBSCRIPTIONS_EXCEEDED":
            return grpc.StatusCode.RESOURCE_EXHAUSTED
        if exc.error_code == "WHOLE_QUOTE_DISABLED":
            return grpc.StatusCode.FAILED_PRECONDITION
        if exc.error_code == "FEATURE_NOT_SUPPORTED":
            return grpc.StatusCode.UNIMPLEMENTED
        if exc.error_code in {"XTDATA_UNAVAILABLE", "SUBSCRIPTION_FAILED"}:
            return grpc.StatusCode.UNAVAILABLE
        return grpc.StatusCode.INVALID_ARGUMENT

    def _error_response(self, context, status_code, message, response_type):
        context.set_code(status_code)
        context.set_details(message)
        return response_type(status=self._status(400, message))
