from __future__ import annotations

from typing import Any, AsyncIterator

from app.services.contracts import QuoteSubscriptionSpec, WholeQuoteSubscriptionSpec
from app.services.xtdata_subscription_hub import XtDataSubscriptionHub


class UiSubscriptionService:
    def __init__(self, hub: XtDataSubscriptionHub):
        self.hub = hub

    def create_quote_subscription(self, spec: QuoteSubscriptionSpec) -> dict[str, Any]:
        subscription_id = self.hub.create_persistent_quote_subscription(spec)
        return self.hub.get_subscription_info(subscription_id) or {"subscription_id": subscription_id}

    def create_whole_quote_subscription(self, spec: WholeQuoteSubscriptionSpec) -> dict[str, Any]:
        subscription_id = self.hub.create_persistent_whole_quote_subscription(spec)
        return self.hub.get_subscription_info(subscription_id) or {"subscription_id": subscription_id}

    def delete_subscription(self, subscription_id: str) -> bool:
        return self.hub.delete_subscription(subscription_id)

    def get_subscription_info(self, subscription_id: str) -> dict[str, Any] | None:
        return self.hub.get_subscription_info(subscription_id)

    def list_subscriptions(self) -> list[dict[str, Any]]:
        return self.hub.list_subscriptions()

    async def stream_subscription(self, subscription_id: str) -> AsyncIterator[dict[str, Any]]:
        async for item in self.hub.stream_async(subscription_id):
            yield item
