from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from config import logger

# Known retailers -> official website. Used as a fallback when a direct
# product URL cannot be resolved. We NEVER fall back to Google Shopping.
RETAILER_HOMEPAGES: Dict[str, str] = {
    "amazon": "https://www.amazon.com",
    "best buy": "https://www.bestbuy.com",
    "bestbuy": "https://www.bestbuy.com",
    "walmart": "https://www.walmart.com",
    "target": "https://www.target.com",
    "costco": "https://www.costco.com",
    "newegg": "https://www.newegg.com",
    "gamestop": "https://www.gamestop.com",
    "playstation": "https://direct.playstation.com",
    "sony": "https://electronics.sony.com",
    "nintendo": "https://www.nintendo.com",
    "xbox": "https://www.xbox.com",
    "microsoft": "https://www.microsoft.com",
    "ebay": "https://www.ebay.com",
    "b&h": "https://www.bhphotovideo.com",
    "b&h photo": "https://www.bhphotovideo.com",
    "micro center": "https://www.microcenter.com",
    "microcenter": "https://www.microcenter.com",
    "adorama": "https://www.adorama.com",
    "dell": "https://www.dell.com",
    "hp": "https://www.hp.com",
    "lenovo": "https://www.lenovo.com",
    "sam's club": "https://www.samsclub.com",
    "samsung": "https://www.samsung.com",
}

_GOOGLE_HOST_MARKERS = ("google.", "shopping.google", "googleusercontent.")


def is_google_url(url: Optional[str]) -> bool:
    """True if the URL points at Google (Shopping/search/redirect)."""
    if not url:
        return False
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return "google." in url.lower()
    return any(marker in host for marker in _GOOGLE_HOST_MARKERS)


def homepage_for(source: Optional[str]) -> Optional[str]:
    """Map a retailer/source name to its official homepage, or None."""
    if not source:
        return None
    normalized = source.strip().lower()
    for key, url in RETAILER_HOMEPAGES.items():
        if key in normalized:
            return url
    return None


def _pick_store_link(stores: List[Dict[str, Any]], source: Optional[str]) -> Optional[str]:
    """Choose the best direct (non-Google) retailer link from immersive stores.

    Prefers the store whose name matches the result's source; otherwise the
    first store that exposes a direct link.
    """
    candidates: List[Dict[str, str]] = []
    for store in stores or []:
        link = store.get("direct_link") or store.get("link")
        if not link or is_google_url(link):
            continue
        candidates.append({"name": str(store.get("name", "")), "link": link})

    if not candidates:
        return None

    if source:
        wanted = source.strip().lower()
        for cand in candidates:
            name = cand["name"].strip().lower()
            if name and (name in wanted or wanted in name):
                return cand["link"]

    return candidates[0]["link"]


def fetch_direct_url(
    immersive_token: Optional[str],
    source: Optional[str],
    api_key: Optional[str] = None,
) -> Optional[str]:
    """Resolve a direct retailer product URL via SerpAPI's immersive product API.

    Returns None (never raises) when the token/key is missing or the call fails.
    """
    if not immersive_token:
        return None

    api_key = api_key or os.getenv("SERPAPI_KEY")
    if not api_key:
        return None

    try:
        from serpapi import GoogleSearch

        response = GoogleSearch(
            {
                "engine": "google_immersive_product",
                "page_token": immersive_token,
                "api_key": api_key,
            }
        ).get_dict()
        stores = response.get("product_results", {}).get("stores", [])
        return _pick_store_link(stores, source)
    except Exception as exc:  # network / API errors must not break the pipeline
        logger.warning("Direct URL lookup failed for %s: %s", source, exc)
        return None


def resolve_item_url(
    item: Dict[str, Any],
    api_key: Optional[str] = None,
    use_immersive: bool = True,
) -> Optional[str]:
    """Resolve the best direct retailer URL for a raw SerpAPI shopping result.

    Order of preference (a Google Shopping URL is NEVER returned):
      1. A direct (non-Google) link already present on the item.
      2. The immersive product API's direct store link (if use_immersive).
      3. The retailer's official homepage (fallback).
    """
    source = item.get("source")

    for key in ("direct_link", "link"):
        candidate = item.get(key)
        if candidate and not is_google_url(candidate):
            return candidate

    if use_immersive:
        direct = fetch_direct_url(
            item.get("immersive_product_page_token"), source, api_key
        )
        if direct:
            return direct

    return homepage_for(source)
