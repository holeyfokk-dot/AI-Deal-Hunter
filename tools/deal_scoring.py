"""Deal scoring heuristics that reduce false positives.

The scorer combines several signals into a ``deal_score`` (0..1, higher is a
better deal) and a ``confidence_score`` (0..1, how much we trust the deal is
real and relevant), and returns human-readable ``reasons`` explaining the score:

  * unrealistic prices (far below the market average) are flagged as likely
    errors/scams instead of "amazing deals";
  * first-party retailers are preferred, third-party marketplace sellers are
    penalized;
  * accessories / listings missing the main product are excluded;
  * refurbished / open-box / used / parts-only / damaged listings are penalized
    unless the query explicitly asked for that condition.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ai import matches_search

# Requirement 3: prefer these first-party retailers.
FIRST_PARTY_RETAILERS = (
    "amazon",
    "walmart",
    "best buy",
    "target",
    "costco",
    "newegg",
    "micro center",
    "microcenter",
    "b&h",
    "b&h photo",
)

# Known third-party marketplaces (in addition to the "Store - Seller" pattern).
KNOWN_MARKETPLACES = (
    "ebay",
    "aliexpress",
    "temu",
    "wish",
    "mercari",
    "poshmark",
    "etsy",
)

# Accessory keywords: a listing is an accessory when one of these appears AND no
# "main product" keyword is present (so "Console with cleaning kit" is kept).
ACCESSORY_KEYWORDS = (
    "controller",
    "case",
    "skin",
    "cover",
    "charger",
    "charging",
    "dock",
    "stand",
    "mount",
    "faceplate",
    "sticker",
    "decal",
    "thumb grip",
    "thumbstick",
    "grip",
    "headset",
    "remote",
    "cable",
    "adapter",
    "screen protector",
    "protector",
    "carrying bag",
    "holder",
    "silicone",
    "cooling fan",
    "cleaning kit",
)

MAIN_PRODUCT_KEYWORDS = (
    "console",
    "processor",
    "cpu",
    "graphics card",
    "gpu",
    "desktop",
    "laptop",
    "monitor",
    "edition",
    "system",
)

# Requirement 5: condition keywords -> (canonical condition, deal_score penalty).
CONDITION_KEYWORDS = {
    "for parts": ("for parts", 0.6),
    "parts only": ("for parts", 0.6),
    "not working": ("for parts", 0.6),
    "as-is": ("for parts", 0.5),
    "as is": ("for parts", 0.5),
    "broken": ("damaged", 0.6),
    "damaged": ("damaged", 0.6),
    "cracked": ("damaged", 0.5),
    "refurbished": ("refurbished", 0.3),
    "renewed": ("refurbished", 0.3),
    "recertified": ("refurbished", 0.3),
    "open box": ("open-box", 0.2),
    "open-box": ("open-box", 0.2),
    "pre-owned": ("used", 0.25),
    "preowned": ("used", 0.25),
    "second hand": ("used", 0.25),
    "second-hand": ("used", 0.25),
    "used": ("used", 0.25),
}

# A price below this fraction of the market average is treated as unrealistic.
UNREALISTIC_RATIO = 0.4

REP_FIRST_PARTY = "first_party"
REP_MARKETPLACE = "marketplace"
REP_UNKNOWN = "unknown"


@dataclass
class ScoreBreakdown:
    deal_score: float
    confidence_score: float
    reputation: str
    reasons: List[str] = field(default_factory=list)
    excluded: bool = False
    exclusion_reason: Optional[str] = None


def parse_price(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def market_average(prices: List[float]) -> Optional[float]:
    """Robust market reference: the median of the available prices."""
    clean = [p for p in prices if isinstance(p, (int, float)) and p > 0]
    if not clean:
        return None
    return float(statistics.median(clean))


def classify_retailer(source: Optional[str]) -> str:
    if not source:
        return REP_UNKNOWN
    normalized = source.strip().lower()

    # "Walmart - SomeSeller" / "Newegg.com - Reseller" => third-party marketplace.
    if " - " in normalized:
        return REP_MARKETPLACE
    if any(mp in normalized for mp in KNOWN_MARKETPLACES):
        return REP_MARKETPLACE
    if any(fp in normalized for fp in FIRST_PARTY_RETAILERS):
        return REP_FIRST_PARTY
    return REP_UNKNOWN


def is_accessory(title: str) -> bool:
    text = (title or "").lower()
    if any(main in text for main in MAIN_PRODUCT_KEYWORDS):
        return False
    return any(acc in text for acc in ACCESSORY_KEYWORDS)


def detect_condition(title: str) -> Optional[str]:
    text = (title or "").lower()
    for keyword, (condition, _penalty) in CONDITION_KEYWORDS.items():
        if keyword in text:
            return condition
    return None


def _condition_penalty(title: str) -> float:
    text = (title or "").lower()
    worst = 0.0
    for keyword, (_condition, penalty) in CONDITION_KEYWORDS.items():
        if keyword in text and penalty > worst:
            worst = penalty
    return worst


def _requested_terms(query: str) -> set:
    return set((query or "").lower().split())


def score_item(
    item: Dict[str, Any],
    query: str,
    market_avg: Optional[float],
    historical_price: Optional[float] = None,
) -> ScoreBreakdown:
    title = item.get("title", "") or ""
    source = item.get("source", "") or ""
    price = parse_price(item.get("price", item.get("extracted_price")))
    reasons: List[str] = []

    reputation = classify_retailer(source)

    # Requirement 4: ignore accessories / non-main-product listings.
    if is_accessory(title):
        return ScoreBreakdown(
            deal_score=0.0,
            confidence_score=0.0,
            reputation=reputation,
            reasons=["Looks like an accessory, not the main product"],
            excluded=True,
            exclusion_reason="accessory",
        )

    if price is None:
        return ScoreBreakdown(
            deal_score=0.0,
            confidence_score=0.0,
            reputation=reputation,
            reasons=["No usable price"],
            excluded=True,
            exclusion_reason="no_price",
        )

    # Requirement 1: value vs market average.
    ratio: Optional[float] = None
    unrealistic = False
    if market_avg and market_avg > 0:
        ratio = price / market_avg

    if ratio is None:
        value = 0.5
        reasons.append("No market average available to compare against")
    elif ratio < UNREALISTIC_RATIO:
        value = 0.05
        unrealistic = True
        reasons.append(
            f"[warn] ${price:.2f} is unrealistically low vs market avg "
            f"${market_avg:.2f} (~{(1 - ratio) * 100:.0f}% off) - likely fake or an error"
        )
    elif ratio < 0.7:
        value = 1.0
        reasons.append(
            f"[+] ~{(1 - ratio) * 100:.0f}% below market avg ${market_avg:.2f} - strong genuine discount"
        )
    elif ratio < 0.9:
        value = 0.8
        reasons.append(
            f"[+] ~{(1 - ratio) * 100:.0f}% below market avg ${market_avg:.2f} - good discount"
        )
    elif ratio <= 1.05:
        value = 0.5
        reasons.append(f"[=] Around market average (${market_avg:.2f})")
    else:
        value = 0.25
        reasons.append(f"[-] Above market average (${market_avg:.2f})")

    deal_score = value
    confidence = 0.5

    # Relevance to the query.
    relevance = matches_search(query, title)
    query_terms = max(len((query or "").split()), 1)
    relevance_norm = min(max(relevance / query_terms, 0.0), 1.0)
    confidence += 0.3 * relevance_norm
    if relevance_norm >= 0.75:
        reasons.append("[+] Strong title match to your search")

    # Requirement 2 & 3: reputation.
    if reputation == REP_FIRST_PARTY:
        deal_score += 0.15
        confidence += 0.2
        reasons.append(f"[+] Sold by first-party retailer ({source})")
    elif reputation == REP_MARKETPLACE:
        deal_score -= 0.25
        confidence -= 0.15
        reasons.append(f"[-] Third-party marketplace seller ({source}) - lower trust")
    else:
        deal_score -= 0.1
        confidence -= 0.1
        reasons.append(f"[-] Unrecognized retailer ({source})")

    if unrealistic:
        confidence -= 0.45

    # Requirement 5: condition penalties unless explicitly requested.
    condition = detect_condition(title)
    if condition:
        requested = _requested_terms(query)
        condition_words = set(condition.split()) | {condition.replace("-", " ")}
        explicitly_requested = bool(condition_words & requested) or condition in (query or "").lower()
        if explicitly_requested:
            reasons.append(f"[=] {condition.capitalize()} condition (explicitly requested)")
        else:
            penalty = _condition_penalty(title)
            deal_score -= penalty
            confidence -= 0.15
            reasons.append(f"[-] Listing looks {condition} - penalized")

    # Requirement 1 (historical): compare to the last-seen price.
    if historical_price and price and not unrealistic:
        if price < historical_price:
            deal_score += 0.05
            reasons.append(
                f"[+] Below last-seen price ${historical_price:.2f} - new low"
            )
        elif price > historical_price * 1.1:
            reasons.append(f"[-] Higher than last-seen price ${historical_price:.2f}")

    if ratio is not None and 0.7 <= ratio <= 1.05:
        confidence += 0.1  # a believable, near-market price

    deal_score = round(min(max(deal_score, 0.0), 1.0), 3)
    confidence = round(min(max(confidence, 0.0), 1.0), 3)

    return ScoreBreakdown(
        deal_score=deal_score,
        confidence_score=confidence,
        reputation=reputation,
        reasons=reasons,
    )
