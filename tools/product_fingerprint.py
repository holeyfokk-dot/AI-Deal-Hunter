"""Product fingerprinting for duplicate detection (Phase 4).

Produces a stable identity for a product so the same item from different
retailers collapses to one deal. Identifiers are used in order of trust:

    GTIN  >  UPC  >  MPN (explicit field)  >  MPN (parsed from title)
          >  Google product_id  >  brand + model + variant (text)

Real global identifiers (GTIN/UPC/MPN) match a product exactly across every
retailer; the text model+variant key is the last-resort fallback. The extractor
is deliberately generic (no retailer-specific rules) and reusable.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from tools.product_relevance import _modifiers, _required_model_tokens, _tokens

# Manufacturer brands used for the text fallback key.
BRANDS = (
    "asus", "msi", "gigabyte", "zotac", "pny", "evga", "sapphire", "xfx",
    "powercolor", "inno3d", "gainward", "palit", "sony", "microsoft",
    "nintendo", "amd", "intel", "nvidia", "dell", "hp", "lenovo", "acer",
    "corsair", "nzxt", "samsung", "apple",
)

# Explicit identifier fields that may appear on a listing (or nested specs).
_GTIN_FIELDS = ("gtin", "gtin13", "gtin14", "gtin12", "gtin8")
_UPC_FIELDS = ("upc", "upc_code", "upce")
_MPN_FIELDS = ("mpn", "manufacturer_part_number", "part_number", "model_number")

# A manufacturer part number: an uppercase alphanumeric code with at least one
# internal hyphen, containing digits (e.g. CFI-7119, 100-100000910WOF,
# 90YV0M80-M0AA00). Requires a digit so plain words never match.
_MPN_RE = re.compile(r"\b(?=[A-Z0-9-]*\d)[A-Z0-9]{2,}(?:-[A-Z0-9]{2,})+\b")

# Reject spec-looking tokens that superficially resemble a part number.
_SPEC_PREFIXES = (
    "DDR", "GDDR", "LPDDR", "PCIE", "PCI", "USB", "HDMI", "WIFI", "SATA",
    "NVME", "MHZ", "GHZ", "RPM", "GBPS", "DP",
)
_SPEC_SUFFIX_RE = re.compile(r"^\d+-(CORE|BIT|PIN|WAY|PACK|ZONE|SLOT|INCH|KEY)$")


def _looks_like_spec(token: str) -> bool:
    up = token.upper()
    lead = re.match(r"^[A-Z]+", up)
    if lead and lead.group() in _SPEC_PREFIXES:
        return True
    if _SPEC_SUFFIX_RE.match(up):
        return True
    return False


def extract_mpn_from_title(title: str) -> Optional[str]:
    """Best-effort manufacturer part number parsed from a product title."""
    candidates = [
        c for c in _MPN_RE.findall(title or "")
        if not _looks_like_spec(c) and len(c.replace("-", "")) >= 5
    ]
    if not candidates:
        return None
    # Prefer the most specific (longest) code.
    return max(candidates, key=lambda c: len(c)).upper()


def _first_field(item: Dict[str, Any], fields) -> Optional[str]:
    for source in (item, item.get("specs") or {}, item.get("about_the_product") or {}):
        if not isinstance(source, dict):
            continue
        for key in fields:
            value = source.get(key)
            if value:
                return str(value).strip()
    return None


def extract_identifiers(item: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Collect any GTIN / UPC / MPN available for a listing."""
    return {
        "gtin": _first_field(item, _GTIN_FIELDS),
        "upc": _first_field(item, _UPC_FIELDS),
        "mpn": _first_field(item, _MPN_FIELDS) or extract_mpn_from_title(item.get("title", "")),
    }


def _brand(title: str) -> str:
    for tok in _tokens(title, keep_stopwords=True):
        if tok in BRANDS:
            return tok
    return ""


def model_text_key(title: str) -> str:
    """Text fallback identity: brand + model tokens + differentiating variant."""
    brand = _brand(title)
    models = ",".join(sorted(set(_required_model_tokens(title))))
    mods = ",".join(sorted(_modifiers(title)))
    return f"{brand}|{models}|{mods}"


def product_fingerprint(item: Dict[str, Any]) -> str:
    """Stable identity for a product, most-trusted signal first."""
    ids = extract_identifiers(item)
    if ids["gtin"]:
        return f"gtin:{ids['gtin']}"
    if ids["upc"]:
        return f"upc:{ids['upc']}"
    if ids["mpn"]:
        return f"mpn:{ids['mpn']}"

    product_id = str(item.get("product_id") or "").strip()
    if product_id:
        return f"pid:{product_id}"

    return f"model:{model_text_key(item.get('title', ''))}"
