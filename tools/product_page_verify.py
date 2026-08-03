"""Phase 4.7 - Behavioral product page verification.

Structural URL checks (HTTPS, not-Google, product-like path) prove a link *looks*
like a product page, but not that it sells the *expected* product. This module
goes a step further: it fetches the page and compares what the page actually
says it is against the search query.

For each candidate URL we extract, most-reliable first:
  1. schema.org ``Product`` JSON-LD (name, brand, sku, gtin, mpn, offers.price,
     offers.availability) - the most reliable signal when present;
  2. the OpenGraph ``og:title``;
  3. the ``<title>`` tag; and the meta description.

The extracted product name is matched against the query using the same
``same_primary_product`` logic used elsewhere, so e.g. an ``RTX 5070`` search is
rejected when the page is really an ``RTX 4070 Super``. Availability is read too,
so out-of-stock listings can be skipped unless stock alerts are requested.

Networked verification is best-effort: many large retailers bot-block automated
requests, so a failed/blocked fetch yields ``unverified`` (not ``mismatch``) and
the caller decides how to treat it.
"""
from __future__ import annotations

import html as _html
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config import logger
from tools.product_relevance import same_primary_product

# Verification outcomes.
VERIFIED = "verified"
MISMATCH = "mismatch"
OUT_OF_STOCK = "out_of_stock"
UNVERIFIED = "unverified"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
_MAX_BYTES = 700_000

# schema.org availability values that mean "can't buy it right now".
_UNAVAILABLE_MARKERS = (
    "outofstock", "sold_out", "soldout", "discontinued", "backorder",
)


@dataclass
class PageVerification:
    status: str
    title: Optional[str] = None
    availability: Optional[str] = None
    identifiers: Dict[str, str] = field(default_factory=dict)
    reason: str = ""

    @property
    def is_mismatch(self) -> bool:
        return self.status == MISMATCH


def fetch_html(url: str, timeout: float = 8.0) -> Optional[str]:
    """Fetch page HTML with a browser-like UA. Returns None on any failure."""
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": _BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(_MAX_BYTES).decode("utf-8", "ignore")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
        logger.info("Page fetch failed for %s: %s", url, exc)
        return None


def _iter_jsonld_products(raw_html: str) -> List[dict]:
    products: List[dict] = []
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        raw_html,
        re.S | re.I,
    )
    for block in blocks:
        try:
            data = json.loads(block.strip())
        except (ValueError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if "Product" in types:
                products.append(node)
    return products


def _meta_content(raw_html: str, key: str) -> Optional[str]:
    for pattern in (
        r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:property|name)=["\']%s["\']',
    ):
        match = re.search(pattern % re.escape(key), raw_html, re.I)
        if match:
            return _html.unescape(match.group(1)).strip()
    return None


def _title_tag(raw_html: str) -> Optional[str]:
    match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.S | re.I)
    return _html.unescape(match.group(1)).strip() if match else None


def extract_product_signals(raw_html: str) -> dict:
    """Pull product name / availability / identifiers from page HTML."""
    name = None
    availability = None
    identifiers: Dict[str, str] = {}

    for product in _iter_jsonld_products(raw_html):
        name = name or product.get("name")
        brand = product.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        for key, value in (
            ("gtin", product.get("gtin13") or product.get("gtin") or product.get("gtin12")),
            ("mpn", product.get("mpn")),
            ("sku", product.get("sku")),
            ("brand", brand),
        ):
            if value and key not in identifiers:
                identifiers[key] = str(value)
        offers = product.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else None
        if isinstance(offers, dict) and availability is None:
            availability = offers.get("availability")
        if name:
            break

    title = name or _meta_content(raw_html, "og:title") or _title_tag(raw_html)
    return {
        "title": title,
        "availability": availability,
        "identifiers": identifiers,
        "meta_description": _meta_content(raw_html, "description"),
    }


def _is_unavailable(availability: Optional[str]) -> bool:
    if not availability:
        return False
    normalized = availability.lower().replace("http://schema.org/", "").replace(
        "https://schema.org/", ""
    )
    return any(marker in normalized for marker in _UNAVAILABLE_MARKERS)


def verify_from_html(raw_html: str, query: str, want_out_of_stock: bool = False) -> PageVerification:
    """Verify already-fetched HTML against a query (no network; unit-testable)."""
    signals = extract_product_signals(raw_html)
    title = signals["title"]
    if not title:
        return PageVerification(UNVERIFIED, reason="No title/schema found on page")

    if not same_primary_product(query, title):
        return PageVerification(
            MISMATCH,
            title=title,
            availability=signals["availability"],
            identifiers=signals["identifiers"],
            reason=f"Page is '{title[:60]}', which does not match '{query}'",
        )

    if _is_unavailable(signals["availability"]) and not want_out_of_stock:
        return PageVerification(
            OUT_OF_STOCK,
            title=title,
            availability=signals["availability"],
            identifiers=signals["identifiers"],
            reason=f"'{title[:50]}' is {signals['availability']}",
        )

    return PageVerification(
        VERIFIED,
        title=title,
        availability=signals["availability"],
        identifiers=signals["identifiers"],
        reason=f"Page '{title[:60]}' matches '{query}'",
    )


def verify_product_page(
    url: str,
    query: str,
    want_out_of_stock: bool = False,
    timeout: float = 8.0,
) -> PageVerification:
    """Fetch ``url`` and verify it actually sells the product from ``query``."""
    raw_html = fetch_html(url, timeout=timeout)
    if not raw_html:
        return PageVerification(
            UNVERIFIED, reason="Could not fetch page (retailer may block bots)"
        )
    return verify_from_html(raw_html, query, want_out_of_stock=want_out_of_stock)
