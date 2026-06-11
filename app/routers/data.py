from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.concurrency import run_in_threadpool

from app.dependencies import (
    get_market_data_service,
    get_reference_data_service,
    get_ui_subscription_service,
    verify_api_key,
)
from app.models.api_requests import (
    FinancialDataRequestModel,
    IndexWeightRequestModel,
    KlineHistoryRequestModel,
    L2RequestModel,
    QuoteSubscriptionRequestModel,
    TickHistoryRequestModel,
    TradingCalendarRequestModel,
    WholeQuoteSubscriptionRequestModel,
)
from app.services.contracts import (
    FinancialDataQuery,
    KlineHistoryQuery,
    L2Query,
    QuoteSubscriptionSpec,
    TickHistoryQuery,
    TradingCalendarQuery,
    WholeQuoteSubscriptionSpec,
)
from app.services.market_data_service import MarketDataService
from app.services.reference_data_service import ReferenceDataService
from app.services.ui_subscription_service import UiSubscriptionService
from app.utils.exceptions import DataServiceException, handle_xtquant_exception
from app.utils.helpers import format_response

router = APIRouter(prefix="/api/v1/data", tags=["数据服务"])


@router.post("/kline-history")
async def get_kline_history(
    request: KlineHistoryRequestModel,
    api_key: str | None = Depends(verify_api_key),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    try:
        items = await run_in_threadpool(
            market_data_service.get_kline_history,
            KlineHistoryQuery(
                symbols=request.symbols,
                period=request.period,
                start_time=request.start_time,
                end_time=request.end_time,
                fields=request.fields,
                adjust_type=request.adjust_type,
                fill_data=request.fill_data,
                auto_download=request.auto_download,
            ),
        )
        return format_response(data={"items": items}, message="获取 K 线历史成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/tick-history")
async def get_tick_history(
    request: TickHistoryRequestModel,
    api_key: str | None = Depends(verify_api_key),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    try:
        items = await run_in_threadpool(
            market_data_service.get_tick_history,
            TickHistoryQuery(
                symbols=request.symbols,
                start_time=request.start_time,
                end_time=request.end_time,
                fields=request.fields,
                adjust_type=request.adjust_type,
                auto_download=request.auto_download,
            ),
        )
        return format_response(data={"items": items}, message="获取 Tick 历史成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/full-tick")
async def get_full_tick_snapshot(
    request: TickHistoryRequestModel,
    api_key: str | None = Depends(verify_api_key),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    try:
        items = await run_in_threadpool(market_data_service.get_full_tick_snapshot, request.symbols)
        return format_response(data={"items": items}, message="获取全量 Tick 快照成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/financial")
async def get_financial_data(
    request: FinancialDataRequestModel,
    api_key: str | None = Depends(verify_api_key),
    reference_data_service: ReferenceDataService = Depends(get_reference_data_service),
):
    try:
        items = reference_data_service.get_financial_data(
            FinancialDataQuery(
                symbols=request.symbols,
                table_names=request.table_names,
                start_time=request.start_time,
                end_time=request.end_time,
            )
        )
        return format_response(data={"items": items}, message="获取财务数据成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.get("/instrument/{symbol}")
async def get_instrument_detail(
    symbol: str,
    complete: bool = Query(False),
    api_key: str | None = Depends(verify_api_key),
    reference_data_service: ReferenceDataService = Depends(get_reference_data_service),
):
    try:
        detail = reference_data_service.get_instrument_detail(symbol, complete=complete)
        return format_response(data=detail, message="获取合约信息成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/trading-calendar")
async def get_trading_calendar(
    request: TradingCalendarRequestModel,
    api_key: str | None = Depends(verify_api_key),
    reference_data_service: ReferenceDataService = Depends(get_reference_data_service),
):
    try:
        calendar = reference_data_service.get_trading_calendar(
            TradingCalendarQuery(
                market=request.market,
                start_time=request.start_time,
                end_time=request.end_time,
            )
        )
        return format_response(data=calendar, message="获取交易日历成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/index-weight")
async def get_index_weight(
    request: IndexWeightRequestModel,
    api_key: str | None = Depends(verify_api_key),
    reference_data_service: ReferenceDataService = Depends(get_reference_data_service),
):
    try:
        weight = reference_data_service.get_index_weight(request.index_code)
        return format_response(data=weight, message="获取指数权重成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.get("/sectors")
async def get_sector_list(
    api_key: str | None = Depends(verify_api_key),
    reference_data_service: ReferenceDataService = Depends(get_reference_data_service),
):
    try:
        sectors = reference_data_service.get_sector_list()
        return format_response(data={"items": sectors}, message="获取板块列表成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/l2/quote")
async def get_l2_quote(
    request: L2RequestModel,
    api_key: str | None = Depends(verify_api_key),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    try:
        items = market_data_service.get_l2_quote(L2Query(request.symbols, request.start_time, request.end_time))
        return format_response(data={"items": items}, message="获取 L2 快照成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/l2/order")
async def get_l2_order(
    request: L2RequestModel,
    api_key: str | None = Depends(verify_api_key),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    try:
        items = market_data_service.get_l2_order(L2Query(request.symbols, request.start_time, request.end_time))
        return format_response(data={"items": items}, message="获取 L2 逐笔委托成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/l2/transaction")
async def get_l2_transaction(
    request: L2RequestModel,
    api_key: str | None = Depends(verify_api_key),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    try:
        items = market_data_service.get_l2_transaction(
            L2Query(request.symbols, request.start_time, request.end_time)
        )
        return format_response(data={"items": items}, message="获取 L2 逐笔成交成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/subscriptions/quote")
async def create_quote_subscription(
    request: QuoteSubscriptionRequestModel,
    api_key: str | None = Depends(verify_api_key),
    ui_subscription_service: UiSubscriptionService = Depends(get_ui_subscription_service),
):
    try:
        info = ui_subscription_service.create_quote_subscription(
            QuoteSubscriptionSpec(
                symbols=request.symbols,
                period=request.period,
                start_time=request.start_time,
                adjust_type=request.adjust_type,
                count=request.count,
            )
        )
        return format_response(data=info, message="创建行情订阅成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.post("/subscriptions/whole-quote")
async def create_whole_quote_subscription(
    request: WholeQuoteSubscriptionRequestModel,
    api_key: str | None = Depends(verify_api_key),
    ui_subscription_service: UiSubscriptionService = Depends(get_ui_subscription_service),
):
    try:
        info = ui_subscription_service.create_whole_quote_subscription(
            WholeQuoteSubscriptionSpec(markets=request.markets)
        )
        return format_response(data=info, message="创建全推订阅成功")
    except DataServiceException as exc:
        raise handle_xtquant_exception(exc)


@router.get("/subscriptions")
async def list_subscriptions(
    api_key: str | None = Depends(verify_api_key),
    ui_subscription_service: UiSubscriptionService = Depends(get_ui_subscription_service),
):
    return format_response(
        data={"items": ui_subscription_service.list_subscriptions()},
        message="获取订阅列表成功",
    )


@router.get("/subscriptions/{subscription_id}")
async def get_subscription_info(
    subscription_id: str,
    api_key: str | None = Depends(verify_api_key),
    ui_subscription_service: UiSubscriptionService = Depends(get_ui_subscription_service),
):
    info = ui_subscription_service.get_subscription_info(subscription_id)
    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "订阅不存在"})
    return format_response(data=info, message="获取订阅详情成功")


@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    api_key: str | None = Depends(verify_api_key),
    ui_subscription_service: UiSubscriptionService = Depends(get_ui_subscription_service),
):
    deleted = ui_subscription_service.delete_subscription(subscription_id)
    return format_response(
        data={"success": deleted, "subscription_id": subscription_id},
        message="订阅已删除" if deleted else "订阅不存在",
    )
