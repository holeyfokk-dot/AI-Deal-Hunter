from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.base_agent import AgentMetadata, BaseAgent
from models.deal_result import DealResult
from models.result_status import ResultStatus
from price_history import load_prices
from tools.deal_scoring import market_average, parse_price, score_item
from tools.retailer_url import resolve_item_url
from tools.search_tool import SearchTool


class Merchant(BaseAgent):
    @classmethod
    def create_metadata(cls) -> AgentMetadata:
        return AgentMetadata(
            name="Merchant",
            version="1.0.0",
            author="AI Deal Hunter",
            description=(
                "Digital Marketplace Specialist for price comparison, deal scoring, "
                "and standardized deal output."
            ),
            capabilities=["search", "compare_prices"],
            priority=10,
            enabled=True,
            required_tools=["search_tool"],
        )

    def can_handle(self, capability: str) -> bool:
        return capability in self.metadata.capabilities

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        query = request.get("query", "")

        raw_response = SearchTool.search(query)
        items = SearchTool.extract_shopping_results(raw_response)

        deals = self._build_deals(query, items)

        status = ResultStatus.SUCCESS
        if not deals:
            status = ResultStatus.NO_RESULTS

        return {
            "status": status,
            "query": query,
            "deals": deals,
        }

    def _build_deals(self, query: str, items: List[Dict[str, Any]]) -> List[DealResult]:
        # Market average (median) across the result set, used to flag
        # unrealistic prices and quantify genuine discounts.
        prices = [
            price
            for price in (parse_price(item.get("price", item.get("extracted_price"))) for item in items)
            if price is not None
        ]
        market_avg = market_average(prices)
        history = load_prices()

        deal_results: List[DealResult] = []

        for item in items:
            current_price = parse_price(item.get("price", item.get("extracted_price")))
            if current_price is None:
                continue

            product_name = item.get("title", "Unknown")
            store = item.get("source", "Unknown")

            breakdown = score_item(
                item,
                query,
                market_avg,
                historical_price=history.get(product_name),
            )

            # Requirement 4: ignore accessories / non-main-product listings.
            if breakdown.excluded:
                continue

            discount = self._parse_discount(item)

            # Never store a Google Shopping URL. Use a direct retailer link when
            # already present, otherwise the retailer homepage as a cheap
            # fallback. The direct product URL is resolved lazily (via the
            # immersive product API) for the deal that actually gets posted, so
            # we avoid an extra API call for every search result here.
            retailer_url = resolve_item_url(item, use_immersive=False)

            deal = DealResult(
                id=str(item.get("product_id") or f"deal-{len(deal_results) + 1}"),
                specialist=self.metadata.name,
                product_name=product_name,
                current_price=current_price,
                historical_lowest_price=history.get(product_name),
                discount_percent=discount,
                store=store,
                store_reputation=breakdown.reputation,
                platform=self._detect_platform(item),
                drm=None,
                region_lock=None,
                bundle_included=False,
                url=retailer_url or "",
                retailer_url=retailer_url,
                deal_score=breakdown.deal_score,
                confidence_score=breakdown.confidence_score,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "immersive_token": item.get("immersive_product_page_token"),
                    "source": store,
                },
                score_reasons=breakdown.reasons,
            )

            deal_results.append(deal)

        return sorted(deal_results, key=lambda deal: deal.deal_score, reverse=True)

    def _parse_discount(self, item: Dict[str, Any]) -> Optional[float]:
        discount = item.get("discount") or item.get("savings")
        if discount is None:
            return None

        try:
            if isinstance(discount, str) and discount.endswith("%"):
                return float(discount.strip(" %"))
            return float(discount)
        except (ValueError, TypeError):
            return None

    def _detect_platform(self, item: Dict[str, Any]) -> Optional[str]:
        title = str(item.get("title", "")).lower()
        if "pc" in title or "steam" in title or "gog" in title:
            return "PC"
        if "ps5" in title or "playstation" in title:
            return "PlayStation"
        if "xbox" in title:
            return "Xbox"
        if "switch" in title:
            return "Nintendo Switch"
        return None
