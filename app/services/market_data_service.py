from __future__ import annotations

from typing import Any, Callable, Iterator

from app.services.contracts import KlineHistoryQuery, L2Query, QuoteSubscriptionSpec, TickHistoryQuery, WholeQuoteSubscriptionSpec
from app.services.xtdata_gateway import XtDataGateway
from app.services.xtdata_subscription_hub import XtDataSubscriptionHub


class MarketDataService:
    def __init__(self, gateway: XtDataGateway, subscription_hub: XtDataSubscriptionHub):
        self.gateway = gateway
        self.subscription_hub = subscription_hub

    def get_kline_history(self, query: KlineHistoryQuery) -> list[dict[str, Any]]:
        return self.gateway.get_kline_history(query)

    def get_tick_history(self, query: TickHistoryQuery) -> list[dict[str, Any]]:
        return self.gateway.get_tick_history(query)

    def get_full_tick_snapshot(self, symbols: list[str]) -> list[dict[str, Any]]:
        return self.gateway.get_full_tick_snapshot(symbols)

    def get_l2_quote(self, query: L2Query) -> list[dict[str, Any]]:
        return self.gateway.get_l2_quote(query)

    def get_l2_order(self, query: L2Query) -> list[dict[str, Any]]:
        return self.gateway.get_l2_order(query)

    def get_l2_transaction(self, query: L2Query) -> list[dict[str, Any]]:
        return self.gateway.get_l2_transaction(query)

    def stream_quote(
        self,
        spec: QuoteSubscriptionSpec,
        stop_checker: Callable[[], bool] | None = None,
    ) -> Iterator[dict[str, Any]]:
        return self.subscription_hub.stream_ephemeral_quote(spec, stop_checker=stop_checker)

    def stream_whole_quote(
        self,
        spec: WholeQuoteSubscriptionSpec,
        stop_checker: Callable[[], bool] | None = None,
    ) -> Iterator[dict[str, Any]]:
        return self.subscription_hub.stream_ephemeral_whole_quote(spec, stop_checker=stop_checker)
