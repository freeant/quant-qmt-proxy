from __future__ import annotations

import grpc

from app.services.contracts import CancelStockOrderCommand, OpenSessionCommand, SubmitStockOrderCommand
from app.services.trading_session_manager import TradingSessionManager
from app.utils.exceptions import TradingServiceException
from generated import common_pb2, trading_pb2, trading_pb2_grpc


ACCOUNT_TYPE_FROM_PROTO = {
    common_pb2.SECURITY_ACCOUNT_TYPE_STOCK: "STOCK",
    common_pb2.SECURITY_ACCOUNT_TYPE_CREDIT: "CREDIT",
    common_pb2.SECURITY_ACCOUNT_TYPE_FUTURE: "FUTURE",
    common_pb2.SECURITY_ACCOUNT_TYPE_FUTURE_OPTION: "FUTURE_OPTION",
    common_pb2.SECURITY_ACCOUNT_TYPE_STOCK_OPTION: "STOCK_OPTION",
    common_pb2.SECURITY_ACCOUNT_TYPE_HUGANGTONG: "HUGANGTONG",
    common_pb2.SECURITY_ACCOUNT_TYPE_SHENGANGTONG: "SHENGANGTONG",
    common_pb2.SECURITY_ACCOUNT_TYPE_NEW3BOARD: "NEW3BOARD",
    common_pb2.SECURITY_ACCOUNT_TYPE_INCOME_SWAP: "INCOME_SWAP",
}
ACCOUNT_TYPE_TO_PROTO = {value: key for key, value in ACCOUNT_TYPE_FROM_PROTO.items()}


class TradingGrpcService(trading_pb2_grpc.TradingServiceServicer):
    def __init__(self, trading_manager: TradingSessionManager):
        self.trading_manager = trading_manager

    def OpenSession(self, request, context):
        try:
            session = self.trading_manager.open_session(
                OpenSessionCommand(
                    account_id=request.account_id,
                    account_type=ACCOUNT_TYPE_FROM_PROTO.get(request.account_type, "STOCK"),
                )
            )
            return trading_pb2.OpenSessionResponse(session=self._to_session_info(session), status=self._status())
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.OpenSessionResponse)

    def CloseSession(self, request, context):
        try:
            success = self.trading_manager.close_session(request.session_id)
            return trading_pb2.CloseSessionResponse(success=success, status=self._status())
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.CloseSessionResponse)

    def GetSession(self, request, context):
        try:
            session = self.trading_manager.get_session(request.session_id)
            return trading_pb2.GetSessionResponse(session=self._to_session_info(session), status=self._status())
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.GetSessionResponse)

    def ListTradingAccounts(self, request, context):
        try:
            accounts = self.trading_manager.list_trading_accounts()
            return trading_pb2.ListTradingAccountsResponse(
                items=[self._to_trading_account_profile(item) for item in accounts],
                status=self._status(),
            )
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.ListTradingAccountsResponse)

    def GetStockAsset(self, request, context):
        try:
            asset = self.trading_manager.get_stock_asset(request.session_id)
            return trading_pb2.GetStockAssetResponse(asset=self._to_stock_asset(asset), status=self._status())
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.GetStockAssetResponse)

    def GetStockPositions(self, request, context):
        try:
            positions = self.trading_manager.get_stock_positions(request.session_id)
            return trading_pb2.GetStockPositionsResponse(
                positions=[self._to_stock_position(item) for item in positions],
                status=self._status(),
            )
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.GetStockPositionsResponse)

    def GetStockOrders(self, request, context):
        try:
            orders = self.trading_manager.get_stock_orders(
                request.session_id,
                cancelable_only=request.cancelable_only,
                strategy_name=request.strategy_name or None,
            )
            return trading_pb2.GetStockOrdersResponse(
                orders=[self._to_stock_order(item) for item in orders],
                status=self._status(),
            )
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.GetStockOrdersResponse)

    def GetStockTrades(self, request, context):
        try:
            trades = self.trading_manager.get_stock_trades(request.session_id)
            return trading_pb2.GetStockTradesResponse(
                trades=[self._to_stock_trade(item) for item in trades],
                status=self._status(),
            )
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.GetStockTradesResponse)

    def SubmitStockOrder(self, request, context):
        try:
            order = self.trading_manager.submit_stock_order(
                SubmitStockOrderCommand(
                    session_id=request.session_id,
                    stock_code=request.stock_code,
                    side=int(request.side),
                    price_type=int(request.price_type),
                    volume=request.volume,
                    price=request.price,
                    strategy_name=request.strategy_name,
                    order_remark=request.order_remark,
                )
            )
            return trading_pb2.SubmitStockOrderResponse(order=self._to_stock_order(order), status=self._status())
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.SubmitStockOrderResponse)

    def CancelStockOrder(self, request, context):
        try:
            target = request.WhichOneof("target")
            if target == "order_id":
                command = CancelStockOrderCommand(session_id=request.session_id, order_id=request.order_id)
            elif target == "sysid_target":
                command = CancelStockOrderCommand(
                    session_id=request.session_id,
                    market=request.sysid_target.market,
                    order_sysid=request.sysid_target.order_sysid,
                )
            else:
                raise TradingServiceException("cancel target is required")

            success = self.trading_manager.cancel_stock_order(command)
            return trading_pb2.CancelStockOrderResponse(success=success, status=self._status())
        except TradingServiceException as exc:
            return self._error_response(context, exc, trading_pb2.CancelStockOrderResponse)

    def StreamTradingEvents(self, request, context):
        try:
            stream = self.trading_manager.stream_events(request.session_id, stop_checker=context.is_active)
            for event in stream:
                yield self._to_trading_event(event)
        except TradingServiceException as exc:
            context.set_code(self._grpc_status_for_error(exc))
            context.set_details(exc.message)

    def _to_session_info(self, session: dict):
        return trading_pb2.SessionInfo(
            session_id=session["session_id"],
            account_id=session["account_id"],
            account_type=ACCOUNT_TYPE_TO_PROTO.get(session.get("account_type", "STOCK"), common_pb2.SECURITY_ACCOUNT_TYPE_STOCK),
            is_real=session.get("is_real", False),
            mode=session.get("mode", ""),
            opened_at_ms=session.get("opened_at_ms", 0),
            environment=session.get("environment", ""),
            account_kind=session.get("account_kind", ""),
            orders_enabled=session.get("orders_enabled", False),
            account_profile=session.get("account_profile", "") or "",
        )

    def _to_trading_account_profile(self, account: dict):
        return trading_pb2.TradingAccountProfile(
            name=account.get("name", ""),
            account_id=account.get("account_id", ""),
            account_type=ACCOUNT_TYPE_TO_PROTO.get(
                account.get("account_type", "STOCK"),
                common_pb2.SECURITY_ACCOUNT_TYPE_STOCK,
            ),
            account_kind=account.get("account_kind", ""),
            orders_enabled=account.get("orders_enabled", False),
        )

    def _to_stock_asset(self, asset: dict):
        return trading_pb2.StockAsset(
            account_id=asset.get("account_id", ""),
            cash=asset.get("cash", 0.0),
            frozen_cash=asset.get("frozen_cash", 0.0),
            market_value=asset.get("market_value", 0.0),
            total_asset=asset.get("total_asset", 0.0),
            fetch_balance=asset.get("fetch_balance", 0.0),
        )

    def _to_stock_position(self, item: dict):
        return trading_pb2.StockPosition(
            account_id=item.get("account_id", ""),
            stock_code=item.get("stock_code", ""),
            instrument_name=item.get("instrument_name", ""),
            volume=item.get("volume", 0),
            can_use_volume=item.get("can_use_volume", 0),
            frozen_volume=item.get("frozen_volume", 0),
            on_road_volume=item.get("on_road_volume", 0),
            yesterday_volume=item.get("yesterday_volume", 0),
            open_price=item.get("open_price", 0.0),
            avg_price=item.get("avg_price", 0.0),
            last_price=item.get("last_price", 0.0),
            market_value=item.get("market_value", 0.0),
            profit_rate=item.get("profit_rate", 0.0),
            direction=item.get("direction", ""),
            secu_account=item.get("secu_account", ""),
        )

    def _to_stock_order(self, item: dict):
        return trading_pb2.StockOrder(
            account_id=item.get("account_id", ""),
            stock_code=item.get("stock_code", ""),
            instrument_name=item.get("instrument_name", ""),
            order_id=item.get("order_id", ""),
            order_sysid=item.get("order_sysid", ""),
            order_time_ms=item.get("order_time_ms", 0),
            order_type=int(item.get("order_type", 0)),
            order_volume=item.get("order_volume", 0),
            price_type=int(item.get("price_type", 0)),
            price=item.get("price", 0.0),
            traded_volume=item.get("traded_volume", 0),
            traded_price=item.get("traded_price", 0.0),
            order_status_code=item.get("order_status_code", 0),
            status_msg=item.get("status_msg", ""),
            strategy_name=item.get("strategy_name", ""),
            order_remark=item.get("order_remark", ""),
            direction=item.get("direction", ""),
            offset_flag=item.get("offset_flag", ""),
            secu_account=item.get("secu_account", ""),
        )

    def _to_stock_trade(self, item: dict):
        return trading_pb2.StockTrade(
            account_id=item.get("account_id", ""),
            stock_code=item.get("stock_code", ""),
            instrument_name=item.get("instrument_name", ""),
            order_type=int(item.get("order_type", 0)),
            traded_id=item.get("traded_id", ""),
            traded_time_ms=item.get("traded_time_ms", 0),
            traded_price=item.get("traded_price", 0.0),
            traded_volume=item.get("traded_volume", 0),
            traded_amount=item.get("traded_amount", 0.0),
            order_id=item.get("order_id", ""),
            order_sysid=item.get("order_sysid", ""),
            strategy_name=item.get("strategy_name", ""),
            order_remark=item.get("order_remark", ""),
            direction=item.get("direction", ""),
            offset_flag=item.get("offset_flag", ""),
            commission=item.get("commission", 0.0),
            secu_account=item.get("secu_account", ""),
        )

    def _to_account_status(self, item: dict):
        return trading_pb2.AccountStatusEvent(
            account_id=item.get("account_id", ""),
            account_type=int(item.get("account_type", common_pb2.SECURITY_ACCOUNT_TYPE_STOCK)),
            status_code=item.get("status_code", 0),
        )

    def _to_order_error(self, item: dict):
        return trading_pb2.OrderErrorEvent(
            account_id=item.get("account_id", ""),
            order_id=item.get("order_id", ""),
            error_id=item.get("error_id", 0),
            error_msg=item.get("error_msg", ""),
            strategy_name=item.get("strategy_name", ""),
            order_remark=item.get("order_remark", ""),
        )

    def _to_cancel_error(self, item: dict):
        return trading_pb2.CancelErrorEvent(
            account_id=item.get("account_id", ""),
            order_id=item.get("order_id", ""),
            order_sysid=item.get("order_sysid", ""),
            error_id=item.get("error_id", 0),
            error_msg=item.get("error_msg", ""),
        )

    def _to_trading_event(self, event: dict):
        payload = event.get("payload", {})
        event_type = event.get("event_type", "")
        message = trading_pb2.TradingEvent(event_time_ms=event.get("event_time_ms", 0))
        if event_type == "account_status":
            message.account_status.CopyFrom(self._to_account_status(payload))
        elif event_type == "asset_update":
            message.asset_update.CopyFrom(self._to_stock_asset(payload))
        elif event_type == "order_update":
            message.order_update.CopyFrom(self._to_stock_order(payload))
        elif event_type == "trade_update":
            message.trade_update.CopyFrom(self._to_stock_trade(payload))
        elif event_type == "position_update":
            message.position_update.CopyFrom(self._to_stock_position(payload))
        elif event_type == "order_error":
            message.order_error.CopyFrom(self._to_order_error(payload))
        elif event_type == "cancel_error":
            message.cancel_error.CopyFrom(self._to_cancel_error(payload))
        return message

    def _status(self, code: int = 0, message: str = "success"):
        return common_pb2.Status(code=code, message=message)

    def _grpc_status_for_error(self, exc: TradingServiceException) -> grpc.StatusCode:
        if exc.error_code == "ORDERS_DISABLED":
            return grpc.StatusCode.PERMISSION_DENIED
        if exc.error_code == "SESSION_NOT_FOUND":
            return grpc.StatusCode.NOT_FOUND
        if exc.error_code == "ACCOUNT_PROFILE_NOT_ALLOWED":
            return grpc.StatusCode.PERMISSION_DENIED
        if exc.error_code == "XTTRADER_UNAVAILABLE":
            return grpc.StatusCode.UNAVAILABLE
        if exc.error_code == "TRADER_NOT_CONNECTED":
            return grpc.StatusCode.FAILED_PRECONDITION
        return grpc.StatusCode.INVALID_ARGUMENT

    def _error_response(self, context, exc: TradingServiceException, response_type):
        context.set_code(self._grpc_status_for_error(exc))
        context.set_details(exc.message)
        return response_type(status=self._status(400, exc.message))
