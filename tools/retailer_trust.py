"""Retailer Trust Engine.

Classifies stores into trust tiers and caps how good a deal can look based on
the seller, so cheap-but-sketchy listings can't outrank trustworthy ones:

    Tier 1  Preferred / first-party  (Amazon, Best Buy, Walmart, ...)   cap 1.00
    Tier 2  Known specialty          (AAAWave, Antonline, Adorama, ...) cap 0.90
    Tier 3  Marketplace              (eBay, AliExpress, "Store - Seller") cap 0.65
    Tier 4  Unknown                  (never-seen store)                 cap 0.45

A never-seen store therefore can never show an "Amazing Deal": its deal score is
capped at 0.45 and its confidence at 0.30. This is deliberately generic (name
matching + the marketplace "Store - Seller" pattern), with no per-retailer logic
beyond the tier membership lists.
"""
from __future__ import annotations

from typing import Optional

# Tier 1 — preferred first-party / major retailers.
TIER1_RETAILERS = (
    "amazon", "best buy", "bestbuy", "walmart", "target", "costco",
    "micro center", "microcenter", "b&h", "b&h photo", "bhphoto",
    "newegg", "gamestop", "playstation", "sony", "nintendo", "apple",
    "microsoft", "xbox", "dell", "hp", "lenovo", "samsung", "nvidia", "amd",
)

# Tier 2 — known specialty retailers (legitimate but niche).
TIER2_RETAILERS = (
    "aaawave", "antonline", "adorama", "memoryc", "provantage",
    "macmall", "tigerdirect", "centralcomputer", "central computers",
    "microcenter", "pcnation", "connection", "cdw",
)

# Tier 3 — third-party marketplaces.
TIER3_MARKETPLACES = (
    "ebay", "aliexpress", "mercari", "temu", "wish", "poshmark", "etsy",
    "alibaba", "walmart marketplace",
)

TIER_SCORE_CAP = {1: 1.00, 2: 0.90, 3: 0.65, 4: 0.45}
TIER_CONFIDENCE_CAP = {1: 1.00, 2: 0.85, 3: 0.50, 4: 0.30}
TIER_NAME = {
    1: "Tier 1 preferred first-party retailer",
    2: "Tier 2 specialty retailer",
    3: "Tier 3 marketplace seller",
    4: "Tier 4 unknown retailer",
}


def classify_tier(source: Optional[str]) -> int:
    """Return the trust tier (1 best .. 4 unknown) for a store name."""
    if not source:
        return 4
    s = source.strip().lower()

    # "Walmart - SomeSeller" / "Newegg.com - Reseller" is a third-party seller.
    if " - " in s:
        return 3
    if any(m in s for m in TIER3_MARKETPLACES):
        return 3
    if any(t in s for t in TIER1_RETAILERS):
        return 1
    if any(t in s for t in TIER2_RETAILERS):
        return 2
    return 4


def score_cap(source: Optional[str]) -> float:
    return TIER_SCORE_CAP[classify_tier(source)]


def confidence_cap(source: Optional[str]) -> float:
    return TIER_CONFIDENCE_CAP[classify_tier(source)]


def tier_name(source: Optional[str]) -> str:
    return TIER_NAME[classify_tier(source)]


def is_trusted(source: Optional[str]) -> bool:
    """Trusted = Tier 1 or Tier 2 (first-party or known specialty)."""
    return classify_tier(source) <= 2


def trust_stars(source: Optional[str], verification_status: Optional[str] = None) -> str:
    """A star rating that's easier to scan than a numeric confidence.

    ★★★★★ Verified · ★★★★ Known retailer · ★★★ Limited history ·
    ★★ Unknown · ★ High Risk. A verified product page upgrades a Tier 1 seller
    to five stars; a page/product mismatch drops any seller to High Risk.
    """
    if verification_status == "mismatch":
        return "★☆☆☆☆ High Risk"

    tier = classify_tier(source)
    if tier == 1:
        if verification_status == "verified":
            return "★★★★★ Verified"
        return "★★★★☆ Known retailer"
    if tier == 2:
        return "★★★★☆ Known retailer"
    if tier == 3:
        return "★★★☆☆ Limited history"
    return "★★☆☆☆ Unknown"


def rating_label(deal_score: float, source: Optional[str]) -> str:
    """Human rating that respects trust: untrusted stores never say "Amazing".

    - Tier 4 (unknown)     -> "Needs Verification"
    - Tier 3 (marketplace) -> "Potential Deal"
    - Tier 2 (specialty)   -> up to "Great Deal"
    - Tier 1 (preferred)   -> up to "Amazing Deal"
    """
    tier = classify_tier(source)
    if tier == 4:
        return "⚠️ Needs Verification"
    if tier == 3:
        return "🟡 Potential Deal"

    if tier == 1 and deal_score >= 0.85:
        return "🔥 Amazing Deal"
    if deal_score >= 0.70:
        return "✅ Great Deal"
    if deal_score >= 0.50:
        return "🟡 Fair Price"
    return "❌ Overpriced"
