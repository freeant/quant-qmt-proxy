from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OpenSessionCommand:
    account_id: str
    account_type: str = "STOCK"


@dataclass(frozen=True)
class SubmitStockOrderCommand:
    session_id: str
    stock_code: str
    side: int
    price_type: int
    volume: int
    price: float = 0.0
    strategy_name: str = ""
    order_remark: str = ""


@dataclass(frozen=True)
class CancelStockOrderCommand:
    session_id: str
    order_id: str | None = None
    market: str | int | None = None
    order_sysid: str | None = None


@dataclass(frozen=True)
class KlineHistoryQuery:
    symbols: list[str]
    period: str
    start_time: str = ""
    end_time: str = ""
    fields: list[str] = field(default_factory=list)
    adjust_type: str = "none"
    fill_data: bool = True


@dataclass(frozen=True)
class TickHistoryQuery:
    symbols: list[str]
    start_time: str = ""
    end_time: str = ""
    fields: list[str] = field(default_factory=list)
    adjust_type: str = "none"


@dataclass(frozen=True)
class FinancialDataQuery:
    symbols: list[str]
    table_names: list[str]
    start_time: str = ""
    end_time: str = ""


@dataclass(frozen=True)
class TradingCalendarQuery:
    market: str
    start_time: str = ""
    end_time: str = ""


@dataclass(frozen=True)
class L2Query:
    symbols: list[str]
    start_time: str = ""
    end_time: str = ""


@dataclass(frozen=True)
class QuoteSubscriptionSpec:
    symbols: list[str]
    period: str = "tick"
    start_time: str = ""
    adjust_type: str = "none"
    count: int = 0


@dataclass(frozen=True)
class WholeQuoteSubscriptionSpec:
    markets: list[str]
