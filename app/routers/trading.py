from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_trading_session_manager, verify_api_key
from app.models.api_requests import (
    CancelStockOrderRequestModel,
    OpenSessionRequestModel,
    SubmitStockOrderRequestModel,
)
from app.services.contracts import CancelStockOrderCommand, OpenSessionCommand, SubmitStockOrderCommand
from app.services.trading_session_manager import TradingSessionManager
from app.utils.exceptions import TradingServiceException, handle_xtquant_exception
from app.utils.helpers import format_response

router = APIRouter(prefix="/api/v1/trading", tags=["交易服务"])

SIDE_TO_XT = {"BUY": 23, "SELL": 24}


@router.post("/sessions")
async def open_session(
    request: OpenSessionRequestModel,
    api_key: str | None = Depends(verify_api_key),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    try:
        session = trading_manager.open_session(OpenSessionCommand(request.account_id, request.account_type))
        return format_response(data=session, message="创建交易会话成功")
    except TradingServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    api_key: str | None = Depends(verify_api_key),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    try:
        return format_response(data=trading_manager.get_session(session_id), message="获取交易会话成功")
    except TradingServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.delete("/sessions/{session_id}")
async def close_session(
    session_id: str,
    api_key: str | None = Depends(verify_api_key),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    try:
        success = trading_manager.close_session(session_id)
        return format_response(
            data={"success": success},
            message="关闭交易会话成功" if success else "交易会话不存在",
        )
    except TradingServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.get("/sessions/{session_id}/asset")
async def get_stock_asset(
    session_id: str,
    api_key: str | None = Depends(verify_api_key),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    try:
        return format_response(data=trading_manager.get_stock_asset(session_id), message="获取资产成功")
    except TradingServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.get("/sessions/{session_id}/positions")
async def get_stock_positions(
    session_id: str,
    api_key: str | None = Depends(verify_api_key),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    try:
        return format_response(
            data={"items": trading_manager.get_stock_positions(session_id)},
            message="获取持仓成功",
        )
    except TradingServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.get("/sessions/{session_id}/orders")
async def get_stock_orders(
    session_id: str,
    cancelable_only: bool = False,
    api_key: str | None = Depends(verify_api_key),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    try:
        return format_response(
            data={"items": trading_manager.get_stock_orders(session_id, cancelable_only=cancelable_only)},
            message="获取订单成功",
        )
    except TradingServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.get("/sessions/{session_id}/trades")
async def get_stock_trades(
    session_id: str,
    api_key: str | None = Depends(verify_api_key),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    try:
        return format_response(
            data={"items": trading_manager.get_stock_trades(session_id)},
            message="获取成交成功",
        )
    except TradingServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/sessions/{session_id}/orders")
async def submit_stock_order(
    session_id: str,
    request: SubmitStockOrderRequestModel,
    api_key: str | None = Depends(verify_api_key),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    try:
        order = trading_manager.submit_stock_order(
            SubmitStockOrderCommand(
                session_id=session_id,
                stock_code=request.stock_code,
                side=SIDE_TO_XT[request.side],
                price_type=request.price_type,
                volume=request.volume,
                price=request.price,
                strategy_name=request.strategy_name,
                order_remark=request.order_remark,
            )
        )
        return format_response(data=order, message="下单成功")
    except TradingServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/sessions/{session_id}/cancel")
async def cancel_stock_order(
    session_id: str,
    request: CancelStockOrderRequestModel,
    api_key: str | None = Depends(verify_api_key),
    trading_manager: TradingSessionManager = Depends(get_trading_session_manager),
):
    try:
        success = trading_manager.cancel_stock_order(
            CancelStockOrderCommand(
                session_id=session_id,
                order_id=request.order_id,
                market=request.market,
                order_sysid=request.order_sysid,
            )
        )
        return format_response(
            data={"success": success},
            message="撤单成功" if success else "撤单失败",
        )
    except TradingServiceException as exc:
        raise handle_xtquant_exception(exc)
