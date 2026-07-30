from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.base_agent import AgentMetadata, BaseAgent
from ai import matches_search
from models.deal_result import DealResult
from models.result_status import ResultStatus
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
        deal_results: List[DealResult] = []
        scores: List[float] = []

        for item in items:
            current_price = self._parse_price(item.get("price"))
            if current_price is None:
                continue

            product_name = item.get("title", "Unknown")
            store = item.get("source", "Unknown")
            url = item.get("product_link", "")
            discount = self._parse_discount(item)
            deal_score = self._calculate_deal_score(current_price, discount)
            confidence = self._calculate_confidence(query, product_name, current_price)

            deal = DealResult(
                id=url or f"deal-{len(deal_results) + 1}",
                specialist=self.metadata.name,
                product_name=product_name,
                current_price=current_price,
                historical_lowest_price=None,
                discount_percent=discount,
                store=store,
                store_reputation="Trusted",
                platform=self._detect_platform(item),
                drm=None,
                region_lock=None,
                bundle_included=False,
                url=url,
                deal_score=deal_score,
                confidence_score=confidence,
                timestamp=datetime.now(timezone.utc),
            )

            deal_results.append(deal)
            scores.append(deal_score)

        return sorted(deal_results, key=lambda deal: deal.deal_score, reverse=True)

    def _parse_price(self, price_value: Any) -> Optional[float]:
        if price_value is None:
            return None

        try:
            return float(str(price_value).replace("$", "").replace(",", ""))
        except (ValueError, TypeError):
            return None

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

    def _calculate_deal_score(self, price: float, discount: Optional[float]) -> float:
        price_score = max(0.0, min(1.0, 500 / (price + 1)))
        discount_score = max(0.0, min(1.0, (discount or 0.0) / 100))
        return round((price_score * 0.6) + (discount_score * 0.4), 3)

    def _calculate_confidence(self, query: str, title: str, price: float) -> float:
        relevance = matches_search(query, title)
        normalized_relevance = min(max(relevance / max(len(query.split()), 1), 0.0), 1.0)
        price_score = max(0.0, min(1.0, 500 / (price + 1)))
        return round((normalized_relevance * 0.7) + (price_score * 0.3), 3)

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
