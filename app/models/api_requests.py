from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class OpenSessionRequestModel(BaseModel):
    account_id: str = Field(..., description="资金账号")
    account_type: str = Field("STOCK", description="账户类型，如 STOCK")


class SubmitStockOrderRequestModel(BaseModel):
    stock_code: str = Field(..., description="标的代码，如 000001.SZ")
    side: str = Field(..., description="买卖方向：BUY 或 SELL")
    price_type: int = Field(..., description="xtquant 价格类型")
    volume: int = Field(..., description="委托数量")
    price: float = Field(0.0, description="委托价格")
    strategy_name: str = Field("", description="策略名称，会传给 QMT 并在订单回报中返回")
    order_remark: str = Field("", description="委托备注")

    @field_validator("side")
    @classmethod
    def validate_side(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"BUY", "SELL"}:
            raise ValueError("side 必须是 BUY 或 SELL")
        return normalized


class CancelStockOrderRequestModel(BaseModel):
    order_id: str | None = Field(None, description="委托编号，与 market+order_sysid 二选一")
    market: str | int | None = Field(None, description="市场：SH/SZ 或 0/1")
    order_sysid: str | None = Field(None, description="柜台合同编号")

    @field_validator("market")
    @classmethod
    def validate_market(cls, value: str | int | None):
        if value is None:
            return value
        if isinstance(value, int):
            return value
        normalized = value.strip().upper()
        return normalized or None


class KlineHistoryRequestModel(BaseModel):
    symbols: list[str] = Field(..., description="标的代码列表")
    period: str = Field("1d", description="K 线周期，如 1d、1m、tick")
    start_time: str = Field("", description="起始时间，如 20240101")
    end_time: str = Field("", description="结束时间")
    fields: list[str] = Field(default_factory=list, description="额外字段")
    adjust_type: str = Field("none", description="复权类型")
    fill_data: bool = Field(True, description="是否填充缺失数据")
    auto_download: bool = Field(True, description="本地无缓存时是否自动从 QMT 下载历史数据")


class TickHistoryRequestModel(BaseModel):
    symbols: list[str] = Field(..., description="标的代码列表")
    start_time: str = Field("", description="起始时间，如 20240101093000")
    end_time: str = Field("", description="结束时间")
    fields: list[str] = Field(default_factory=list, description="额外字段")
    adjust_type: str = Field("none", description="复权类型")
    auto_download: bool = Field(True, description="本地无缓存时是否自动从 QMT 下载历史数据")


class FinancialDataRequestModel(BaseModel):
    symbols: list[str] = Field(..., description="标的代码列表")
    table_names: list[str] = Field(..., description="财务表名，如 Balance")
    start_time: str = Field("", description="起始时间")
    end_time: str = Field("", description="结束时间")


class IndexWeightRequestModel(BaseModel):
    index_code: str = Field(..., description="指数代码")


class TradingCalendarRequestModel(BaseModel):
    market: str = Field(..., description="市场，如 SH、SZ")
    start_time: str = Field("", description="起始日期")
    end_time: str = Field("", description="结束日期")


class L2RequestModel(BaseModel):
    symbols: list[str] = Field(..., description="标的代码列表")
    start_time: str = Field("", description="起始时间")
    end_time: str = Field("", description="结束时间")


class QuoteSubscriptionRequestModel(BaseModel):
    symbols: list[str] = Field(..., description="订阅标的列表")
    period: str = Field("tick", description="周期：tick 或 K 线周期")
    start_time: str = Field("", description="起始时间")
    adjust_type: str = Field("none", description="复权类型")
    count: int = Field(0, description="回放条数；0 表示仅实时；-1 为 tick 全历史（tick 周期下不支持）")

    @field_validator("count")
    @classmethod
    def validate_count(cls, value: int) -> int:
        if value < -1:
            raise ValueError("count 必须大于等于 -1")
        return value


class WholeQuoteSubscriptionRequestModel(BaseModel):
    markets: list[str] = Field(default_factory=lambda: ["SH", "SZ"], description="全推市场列表")
