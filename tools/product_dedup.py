"""Duplicate suppression / product consolidation.

The same product is frequently returned multiple times (the same listing twice,
or the same product from several sellers). This module collapses those into a
single product and picks the best offer, so the bot posts one deal per product
instead of many near-duplicates:

    RTX 5070 ASUS TUF OC
      Amazon   $589
      Best Buy $579
      Newegg   $574   <- best offer
      Walmart  $599
    => one product, best offer = Newegg $574

Products are identified by Google's catalog ``product_id`` when available, with a
brand + model + variant fallback otherwise. This is the closest identifier we get
from SerpAPI today; matching on GTIN / UPC / MPN is the natural next step.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from tools.deal_scoring import UNREALISTIC_RATIO, parse_price
from tools.product_fingerprint import product_fingerprint


def canonical_product_key(item: Dict[str, Any]) -> str:
    """A stable identity for a product across duplicate listings / sellers.

    Delegates to :func:`product_fingerprint`, which prefers real identifiers
    (GTIN / UPC / MPN) and falls back to Google's product_id and then to a
    brand + model + variant text key.
    """
    return product_fingerprint(item)


def consolidate_offers(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Cluster listings that refer to the same product."""
    clusters: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        clusters.setdefault(canonical_product_key(item), []).append(item)
    return clusters


def best_offer(
    items: List[Dict[str, Any]],
    market_avg: Optional[float] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Pick the best (cheapest realistic) offer for a product; return the rest.

    Unrealistically low prices (likely fake/errors) are not chosen as the best
    offer when a realistic alternative exists.
    """
    priced: List[Tuple[float, Dict[str, Any]]] = []
    for item in items:
        price = parse_price(item.get("price", item.get("extracted_price")))
        if price is not None:
            priced.append((price, item))

    if not priced:
        return items[0], []

    realistic = [
        (p, it)
        for p, it in priced
        if not (market_avg and market_avg > 0 and p < UNREALISTIC_RATIO * market_avg)
    ]
    pool = realistic or priced

    best_price, best_item = min(pool, key=lambda pair: pair[0])

    others = [
        {"store": it.get("source", "Unknown"), "price": p}
        for p, it in sorted(priced, key=lambda pair: pair[0])
        if it is not best_item
    ]
    return best_item, others
