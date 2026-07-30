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

### Known app-level gotcha (not an environment issue)
`app.run()` reads `item["title"]`/`item["price"]`, but `Merchant` emits serialized
`DealResult` dicts keyed `product_name`/`current_price`. So the `main.py` → Merchant path
prints "No matching products found" even with valid results. The correctly-working deal
scoring is observed by inspecting `Merchant.handle()` / `AgentManager.route()` output directly.
