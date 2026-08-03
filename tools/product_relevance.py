"""Product relevance & grouping that runs BEFORE deal scoring.

Goals (reduce apples-to-oranges comparisons):
  * classify each listing into a product type (CPU / GPU / CONSOLE / ACCESSORY /
    PREBUILT_PC), and detect bundles;
  * reject listings that don't refer to the same primary product as the query
    (e.g. a CPU query must not match a full prebuilt PC that merely contains that
    CPU, a "RTX 5070" query must not match an "RTX 5090", a console query must
    not match a controller);
  * group the survivors by (product_type, is_bundle) so the market average and
    scoring are computed within a like-for-like group.

Requirement 4 asks for "embeddings or semantic similarity". We use a lightweight,
dependency-free semantic similarity: a bag-of-words cosine over normalized tokens
(with retailer/console synonyms folded in). It behaves like a tiny embedding and
runs offline / in CI. A heavier sentence-embedding model could be swapped into
``semantic_similarity`` later without changing callers.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from tools.deal_scoring import is_accessory


class ProductType(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    CONSOLE = "console"
    ACCESSORY = "accessory"
    PREBUILT_PC = "prebuilt_pc"
    OTHER = "other"


GPU_MARKERS = (
    "geforce", "radeon", "graphics card", "graphics processor", "gpu",
    "rtx", "gtx", "rx 7", "rx 9", "rx 6", "intel arc", "arc a", "arc b",
)
CPU_MARKERS = (
    "ryzen", "core i3", "core i5", "core i7", "core i9", "threadripper",
    "processor", "cpu", "-core", " core processor",
)
CONSOLE_MARKERS = (
    "playstation", "ps5", "ps4", "xbox", "nintendo switch", "switch 2",
    "game console", "console",
)
PREBUILT_KEYWORDS = (
    "gaming pc", "gaming desktop", "prebuilt", "pre-built", "desktop computer",
    "tower pc", "gaming system", "gaming rig", "barebones", "gaming tower",
)
BUNDLE_KEYWORDS = ("bundle", "combo", " + ", "2-game", "two-game", "value pack")
GAME_WORDS = (
    "mario", "zelda", "donkey kong", "kart", "nba 2k", "call of duty",
    "spider-man", "spiderman", "hogwarts", "fortnite", "minecraft",
    "astro bot", "god of war", "bananza",
)

# Modifiers that make a DIFFERENT product (e.g. RTX 5070 vs 5070 Ti, PS5 vs PS5 Pro).
DIFFERENTIATING_MODS = ("pro", "ti", "super", "max", "ultra", "xt", "xtx")

SIMILARITY_THRESHOLD = 0.28

_RAM_RE = re.compile(r"\d+\s*gb\s*ddr\d", re.I)
_STORAGE_RE = re.compile(r"\d+\s*(tb|gb)\s*(ssd|nvme|hdd)", re.I)
_STOPWORDS = {
    "the", "a", "an", "for", "with", "and", "by", "new", "of", "in", "to",
    "gaming", "game", "edition", "series", "gen", "generation", "oc", "graphics",
    "card", "console", "processor", "cpu", "gpu", "desktop", "system",
}


def _normalize(text: str) -> str:
    t = (text or "").lower()
    # Fold console synonyms (but do NOT blanket-map "playstation" -> ps5, or a
    # "PlayStation 4" listing would be mistaken for a PS5).
    t = t.replace("playstation 5", " ps5 ").replace("playstation5", " ps5 ")
    t = t.replace("play station 5", " ps5 ")
    t = t.replace("nintendo switch", " switch ")
    t = t.replace("xbox series x", " xboxseriesx ").replace("xbox series s", " xboxseriess ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t


def _tokens(text: str, keep_stopwords: bool = False) -> List[str]:
    toks = _normalize(text).split()
    if keep_stopwords:
        return toks
    return [tok for tok in toks if tok not in _STOPWORDS]


def semantic_similarity(a: str, b: str) -> float:
    """Cosine similarity over normalized token vectors (a tiny embedding)."""
    ca, cb = Counter(_tokens(a)), Counter(_tokens(b))
    if not ca or not cb:
        return 0.0
    common = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in common)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _has_any(text: str, markers) -> bool:
    return any(m in text for m in markers)


def is_prebuilt_pc(title: str) -> bool:
    t = (title or "").lower()
    if _has_any(t, PREBUILT_KEYWORDS):
        return True
    # A full system names both a CPU and a GPU (and usually storage).
    has_cpu = _has_any(t, ("ryzen", "core i", "intel", "threadripper"))
    has_gpu = _has_any(t, ("geforce", "radeon", "rtx", "gtx", "arc "))
    if has_cpu and has_gpu:
        return True
    if _RAM_RE.search(t) and _STORAGE_RE.search(t):
        return True
    return False


def is_bundle(title: str) -> bool:
    t = (title or "").lower()
    return _has_any(t, BUNDLE_KEYWORDS) or _has_any(t, GAME_WORDS)


def classify_product_type(title: str) -> ProductType:
    t = (title or "").lower()
    if is_prebuilt_pc(title):
        return ProductType.PREBUILT_PC
    if is_accessory(title):
        return ProductType.ACCESSORY
    if _has_any(t, GPU_MARKERS):
        return ProductType.GPU
    if _has_any(t, CPU_MARKERS):
        return ProductType.CPU
    if _has_any(t, CONSOLE_MARKERS):
        return ProductType.CONSOLE
    return ProductType.OTHER


def classify_query_type(query: str) -> ProductType:
    return classify_product_type(query)


def _required_model_tokens(text: str) -> List[str]:
    """Tokens that pin the product/version (5070, 7800x3d, ps5, the "2" in Switch 2)."""
    return [tok for tok in _tokens(text, keep_stopwords=True) if any(ch.isdigit() for ch in tok)]


def _modifiers(text: str) -> set:
    toks = set(_tokens(text, keep_stopwords=True))
    return {m for m in DIFFERENTIATING_MODS if m in toks}


def same_primary_product(query: str, title: str) -> bool:
    """True if the title refers to the same primary product as the query."""
    title_tokens = set(_tokens(title, keep_stopwords=True))

    # 1. Every model/version identifier in the query must appear in the title
    #    (RTX 5070 != 5090, Switch 2 != Switch, PS5 != PS4).
    required = _required_model_tokens(query)
    if required and not all(tok in title_tokens for tok in required):
        return False

    # 2. Differentiating modifiers must match exactly (PS5 vs PS5 Pro, 5070 vs 5070 Ti).
    if _modifiers(query) != _modifiers(title):
        return False

    # 3. With a pinned model we accept; otherwise fall back to semantic similarity.
    if required:
        return True
    return semantic_similarity(query, title) >= SIMILARITY_THRESHOLD


def is_relevant(query: str, item: Dict[str, Any]) -> Tuple[bool, str]:
    """Decide whether an item should be scored for this query (req 2 & 6)."""
    title = item.get("title", "") or ""
    qt = classify_query_type(query)
    it = classify_product_type(title)

    # Controllers/accessories are never the answer to a main-product query.
    if it == ProductType.ACCESSORY and qt != ProductType.ACCESSORY:
        return False, "accessory, not the main product"

    # CPUs/GPUs/consoles must not be compared against full prebuilt PCs.
    if it == ProductType.PREBUILT_PC and qt in (
        ProductType.CPU, ProductType.GPU, ProductType.CONSOLE,
    ):
        return False, "full PC build, not the requested component"

    # Different product categories are never compared.
    if qt != ProductType.OTHER and it != qt:
        return False, f"different product type ({it.value} vs requested {qt.value})"

    if not same_primary_product(query, title):
        return False, "different model / variant"

    return True, "matches the requested product"


def group_key(product_type: ProductType, bundle: bool) -> str:
    return f"{product_type.value}_bundle" if bundle else product_type.value


def group_results(query: str, items: List[Dict[str, Any]]) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    """Return (groups keyed by product_type[/bundle], rejected items).

    Bundles are separated into their own group so they're scored against other
    bundles rather than against standalone products (req 2 & 3). Market averages
    should be computed per returned group (req 5).
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    rejected: List[Dict[str, Any]] = []

    for item in items:
        ok, reason = is_relevant(query, item)
        if not ok:
            rejected.append({"item": item, "reason": reason})
            continue
        title = item.get("title", "") or ""
        key = group_key(classify_product_type(title), is_bundle(title))
        groups.setdefault(key, []).append(item)

    return groups, rejected
