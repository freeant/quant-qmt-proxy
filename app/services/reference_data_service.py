from __future__ import annotations

from typing import Any

from app.services.contracts import FinancialDataQuery, TradingCalendarQuery
from app.services.xtdata_gateway import XtDataGateway


class ReferenceDataService:
    def __init__(self, gateway: XtDataGateway):
        self.gateway = gateway

    def get_financial_data(self, query: FinancialDataQuery) -> list[dict[str, Any]]:
        return self.gateway.get_financial_data(query)

    def get_instrument_detail(self, symbol: str, complete: bool = False) -> dict[str, Any]:
        return self.gateway.get_instrument_detail(symbol, complete=complete)

    def get_trading_calendar(self, query: TradingCalendarQuery) -> dict[str, Any]:
        return self.gateway.get_trading_calendar(query)

    def get_index_weight(self, index_code: str) -> dict[str, Any]:
        return self.gateway.get_index_weight(index_code)

    def get_sector_list(self) -> list[dict[str, Any]]:
        return self.gateway.get_sector_list()
