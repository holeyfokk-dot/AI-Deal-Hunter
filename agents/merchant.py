from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.base_agent import AgentMetadata, BaseAgent
from models.deal_result import DealResult
from models.result_status import ResultStatus
from price_history import load_prices
from tools.deal_scoring import market_average, parse_price, score_item
from tools.product_dedup import best_offer, consolidate_offers
from tools.product_relevance import classify_product_type, group_results
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
        history = load_prices()

        # Group by product type first, and reject unrelated listings (full PCs
        # for a CPU/GPU query, controllers for a console query, wrong models,
        # etc.) BEFORE scoring. Bundles are grouped separately.
        groups, _rejected = group_results(query, items)

        deal_results: List[DealResult] = []

        for group_name, group_items in groups.items():
            # Market average (median) is computed within the like-for-like group.
            group_prices = [
                price
                for price in (
                    parse_price(item.get("price", item.get("extracted_price")))
                    for item in group_items
                )
                if price is not None
            ]
            group_avg = market_average(group_prices)
            group_size = len(group_items)

            # Duplicate suppression: collapse the same product (across duplicate
            # rows / sellers) into one, and pick the best offer.
            clusters = consolidate_offers(group_items)

            for cluster_items in clusters.values():
                item, other_offers = best_offer(cluster_items, group_avg)

                current_price = parse_price(item.get("price", item.get("extracted_price")))
                if current_price is None:
                    continue

                product_name = item.get("title", "Unknown")
                store = item.get("source", "Unknown")

                breakdown = score_item(
                    item,
                    query,
                    group_avg,
                    historical_price=history.get(product_name),
                )

                if breakdown.excluded:
                    continue

                discount = self._parse_discount(item)

                # Never store a Google Shopping URL. Use a direct retailer link
                # when already present, otherwise the retailer homepage as a
                # cheap fallback. The direct product URL is resolved lazily (via
                # the immersive product API) for the deal that actually gets
                # posted, so we avoid an extra API call for every search result.
                retailer_url = resolve_item_url(item, use_immersive=False)

                reasons = [
                    f"[+] Matched product group '{group_name}' "
                    f"(compared against {group_size} like-for-like listing(s))"
                ]
                if other_offers:
                    cheapest_alt = ", ".join(
                        f"{o['store']} ${o['price']:.2f}" for o in other_offers[:3]
                    )
                    reasons.append(
                        f"[+] Best of {len(other_offers) + 1} offers for this product "
                        f"(also: {cheapest_alt})"
                    )
                reasons += breakdown.reasons

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
                    bundle_included=group_name.endswith("_bundle"),
                    url=retailer_url or "",
                    retailer_url=retailer_url,
                    deal_score=breakdown.deal_score,
                    confidence_score=breakdown.confidence_score,
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "immersive_token": item.get("immersive_product_page_token"),
                        "source": store,
                        "product_type": classify_product_type(product_name).value,
                        "product_group": group_name,
                        "offer_count": len(other_offers) + 1,
                        "other_offers": other_offers,
                    },
                    score_reasons=reasons,
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
