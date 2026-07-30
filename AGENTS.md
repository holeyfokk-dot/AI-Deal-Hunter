# AGENTS.md

## Cursor Cloud specific instructions

### Product
AI Deal Hunter — a single Python 3.12 app (CLI + Discord bot). It scans `watchlist.json`,
searches product prices, scores/ranks deals via an internal agent framework (`agents/`,
`manager/`), tracks price history in `prices.json`, and posts alerts to Discord. There is
no database, web server, or build step; persistence is local JSON files.

### Dependencies
Python deps are installed by the startup update script (there is no dependency manifest in
the base repo other than `requirements.txt`). The import name `serpapi` (`from serpapi import
GoogleSearch`) is provided by the PyPI package `google-search-results`, NOT the newer
`serpapi` package — do not swap it.

### Run / test / lint
- Tests (no secrets needed): `python -m unittest discover -p "test_*.py"`.
  Known/pre-existing: 3 failures in `test_lightning_mcqueen.py` assert plain strings (e.g.
  `"ok"`) against `ResultStatus` enum members — a scaffolding bug unrelated to setup. The 9
  merchant/VIN tests pass.
- Full app: `python main.py`. It is interactive (prompts on stdin for a ZIP/city) and
  requires real secrets. `discord_config.py` raises `ValueError` at import time if
  `DISCORD_TOKEN` or `CHANNEL_ID` are unset, so the whole app cannot start without them; real
  price search additionally needs `SERPAPI_KEY` (a paid SerpAPI account). Set these in a
  `.env` file (see `.env.example`, gitignored) or as env vars.
- No linter/formatter is configured; there is no build step.

### Testing the core without secrets
The genuine core (agent auto-discovery, `AgentManager.route("search", ...)`, and the
`Merchant` deal scoring/ranking) can be exercised without Discord/SerpAPI by stubbing the
single external HTTP boundary `search_api.google_shopping_search` (also imported by name in
`tools/search_tool.py`, so patch it in both). Run harness scripts with `PYTHONPATH=/workspace`.

### Duplicate suppression (one product per deal)
`tools/product_dedup.py` runs inside `Merchant._build_deals` after grouping:
`consolidate_offers` clusters listings by `canonical_product_key` (Google `product_id`,
else brand+model+variant), and `best_offer` picks the cheapest realistic offer per cluster
(skipping unrealistic lowballs). One `DealResult` is emitted per product; the alternatives
are stored in `metadata["other_offers"]` and shown as "Also available at" in the embed.
Limitation: SerpAPI's immersive stores don't include per-seller prices and `google_product`
isn't available on this key, so cross-retailer price comparison uses the shopping-result
rows. Matching by GTIN/UPC/MPN is the intended next step.

### Product relevance / grouping (before scoring)
`tools/product_relevance.py` runs before scoring in `Merchant._build_deals`:
`group_results(query, items)` classifies each listing (`classify_product_type`:
CPU/GPU/CONSOLE/ACCESSORY/PREBUILT_PC), rejects unrelated listings (full PCs for a
CPU/GPU query, controllers for a console query, wrong model/variant via
`same_primary_product`), detects bundles (`is_bundle`) into a separate group, and the
scorer's market average is then computed per group. Semantic matching is a dependency-free
token-cosine (`semantic_similarity`) plus required model tokens (5070, 7800x3d, the "2" in
Switch 2) and differentiating modifiers (pro/ti/super/...); a real embedding model could be
swapped into `semantic_similarity` without changing callers. Caveat: the median market
average can still be inflated by scalper listings (no MSRP database yet), so a legit unit may
show a large "discount" vs an inflated median.

### Deal scoring
`tools/deal_scoring.py` produces `deal_score`/`confidence_score` + `reasons`, used by
`Merchant._build_deals`. It flags unrealistic prices (vs the median market average and
last-seen price), penalizes third-party marketplace sellers, boosts the first-party
retailers in `FIRST_PARTY_RETAILERS`, excludes accessories (`is_accessory`), and penalizes
refurbished/open-box/used/parts-only/damaged listings unless the query asks for them.
Reasons are stored in `DealResult.score_reasons` and shown in the Discord embed / console.
The market average is a median computed per relevance group (see below), so mixed listing
types (full PCs, wrong variants) no longer skew it; scalper-inflated medians can still remain.

### Deal URLs (direct retailer links)
Deal alerts must link to the retailer's product page, never a Google Shopping URL.
- `tools/retailer_url.py` resolves URLs: a direct (non-Google) link on the item →
  the `google_immersive_product` API's store link (`product_results.stores[].link`) →
  the retailer homepage (`RETAILER_HOMEPAGES`) as a non-Google fallback.
- Cost control: the immersive lookup runs only for the **posted** best deal
  (`app.resolve_direct_url`), not for every search result. `Merchant` sets the cheap
  homepage fallback (`resolve_item_url(..., use_immersive=False)`) and stashes the
  `immersive_product_page_token` in `DealResult.metadata` for later resolution.
- The direct URL lives in `DealResult.retailer_url`; `discord_bot.send_deal()` posts an
  embed whose "Buy Now" button links to it.

### Note on `app.run()` (previously broken, now fixed)
`app.run()` used to read `title`/`price` while `Merchant` emitted
`product_name`/`current_price`, so the scan always printed "No matching products found".
It now consumes the `DealResult` schema directly, finds a best deal, and posts it.
`main.py` remains interactive (`input()`), so CI/non-interactive runs still use
`echo "" | python main.py`.

### CI automation
`.github/workflows/deal-hunter.yml` runs `main.py` end-to-end on push to `main`,
`workflow_dispatch`, and a daily `13:00 UTC` cron. Non-obvious points:
- `main.py` calls `input()` for an optional ZIP/city, so CI runs it as
  `echo "" | python main.py` to avoid an `EOFError` on empty stdin.
- Secrets (`SERPAPI_KEY`, `DISCORD_TOKEN`, `CHANNEL_ID`) are injected as env vars from
  GitHub Actions secrets; a preflight step fails the job with a clear message (not a
  Python traceback) if any are missing. They are never committed (`.env` is git-ignored).
- The Discord client runs in a daemon thread, so the process exits cleanly once the
  watchlist scan finishes; the job also has a 10-minute timeout as a safety net.
- Real runs consume SerpAPI credits and post to the live Discord channel — every push to
  `main` and every daily cron triggers a real run.
