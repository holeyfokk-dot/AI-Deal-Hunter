# AI Deal Hunter

A Python CLI + Discord bot that scans a product watchlist, searches live prices
via SerpAPI (Google Shopping), scores/ranks deals with a small internal agent
framework, tracks price history, and posts deal alerts to a Discord channel.

## Requirements

- Python 3.12 (3.10+ should work)
- A [SerpAPI](https://serpapi.com/) API key (live price search)
- A [Discord bot](https://discord.com/developers/applications) token and a target channel ID

## Install

```bash
pip install -r requirements.txt
```

## Configuration / Secrets

The app reads three values from environment variables (loaded from a local
`.env` file via `python-dotenv`, or from the process environment directly). **No
credentials are stored in the repo** — `.env` is git-ignored.

| Variable        | Required | Purpose                                                        |
|-----------------|----------|----------------------------------------------------------------|
| `SERPAPI_KEY`   | yes      | SerpAPI key for Google Shopping searches                       |
| `DISCORD_TOKEN` | yes      | Discord bot token (validated at import; app won't start if unset) |
| `CHANNEL_ID`    | yes      | Numeric Discord channel ID for alerts (validated at import)    |
| `LOG_LEVEL`     | no       | `INFO` (default) or `DEBUG` for verbose logging                |

### Local setup

```bash
cp .env.example .env
# then edit .env and fill in SERPAPI_KEY, DISCORD_TOKEN, CHANNEL_ID
```

Enable Developer Mode in Discord, right-click the target channel, and choose
**Copy Channel ID** to get `CHANNEL_ID`.

## Run locally

```bash
python main.py
```

`main.py` starts the Discord bot, waits for it to connect, prompts for an
optional ZIP/city, then scans `watchlist.json` and posts alerts. To run it
non-interactively (e.g. in CI), pipe an empty line for the prompt:

```bash
echo "" | python main.py
```

## Tests

```bash
python -m unittest discover -p "test_*.py"
```

## Automation (GitHub Actions)

The workflow at [`.github/workflows/deal-hunter.yml`](.github/workflows/deal-hunter.yml)
runs the bot pipeline (`main.py`) end-to-end on three triggers:

- **push to `main`**
- **manual dispatch** (Actions tab → *AI Deal Hunter* → *Run workflow*)
- **daily schedule** at `13:00 UTC`

What it does, step by step:

1. Checks out the repo and sets up Python 3.12 (with pip caching).
2. Installs dependencies from `requirements.txt`.
3. **Validates secrets** — if `SERPAPI_KEY`, `DISCORD_TOKEN`, or `CHANNEL_ID` is
   missing, it logs a clear error and fails the job (no Python traceback).
4. Runs the pipeline non-interactively (`echo "" | python main.py`) with the
   secrets injected as environment variables and `LOG_LEVEL=INFO`.

A 10-minute job timeout and a `concurrency` group prevent hung or overlapping runs.

### Configure the Actions secrets

Add these as encrypted repository secrets (they are injected as env vars only at
run time and never committed):

**Settings → Secrets and variables → Actions → New repository secret**

- `SERPAPI_KEY`
- `DISCORD_TOKEN`
- `CHANNEL_ID`

Or with the GitHub CLI:

```bash
gh secret set SERPAPI_KEY
gh secret set DISCORD_TOKEN
gh secret set CHANNEL_ID
```

### Test the automation locally

You don't need to push to verify the workflow logic — reproduce the two key
steps locally (secrets come from your `.env` / shell env, never the repo):

```bash
# Load your local secrets first (so the guard/pipeline can see them)
set -a && . ./.env && set +a

# 1) Validate the workflow YAML parses
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deal-hunter.yml')); print('workflow YAML OK')"

# 2) Reproduce the secret-guard step (fails clearly if any are unset)
missing=0
for name in SERPAPI_KEY DISCORD_TOKEN CHANNEL_ID; do
  if [ -z "${!name}" ]; then echo "Missing required secret: $name"; missing=1; fi
done
[ "$missing" -eq 0 ] && echo "All required secrets present" || exit 1

# 3) Run the exact pipeline command the workflow runs
echo "" | LOG_LEVEL=INFO python3 main.py
```

To run the whole workflow in a local container, install
[`act`](https://github.com/nektos/act) and run:

```bash
act workflow_dispatch -W .github/workflows/deal-hunter.yml \
  -s SERPAPI_KEY="$SERPAPI_KEY" -s DISCORD_TOKEN="$DISCORD_TOKEN" -s CHANNEL_ID="$CHANNEL_ID"
```

## Product relevance & grouping (runs before scoring)

Before anything is scored, `tools/product_relevance.py` classifies each listing
and rejects apples-to-oranges matches so deals are only compared like-for-like:

- **Product-type classification** — CPU / GPU / CONSOLE / ACCESSORY / PREBUILT_PC.
- **Rejections before scoring** — a CPU/GPU query never matches a full prebuilt
  PC; a console query never matches a controller; a `RTX 5070` query never
  matches an `RTX 5090` or `5070 Ti`; a `PlayStation 5` query never matches a
  `PS5 Pro`; a `Switch 2` query never matches the original `Switch`.
- **Bundle detection** — bundles/combos (console + game, CPU + motherboard) are
  put in a separate group and scored against other bundles, not standalone units.
- **Semantic similarity** — a lightweight, dependency-free bag-of-words cosine
  (`semantic_similarity`) plus exact model/variant token matching decides whether
  two titles refer to the same primary product. (A heavier sentence-embedding
  model could be dropped into `semantic_similarity` later.)
- **Per-group market average** — the median used by the scorer is computed only
  within a product group, so a $1,500 prebuilt no longer inflates a CPU's
  "market average".

## Duplicate suppression (one product, best offer)

`tools/product_dedup.py` collapses duplicate listings of the same product (the
same row twice, or the same product from multiple sellers) into a single product
and picks the **best (cheapest realistic) offer**, so the bot posts one deal per
product instead of many near-duplicates:

```
RTX 5070 ASUS TUF OC → Amazon $589 · Best Buy $579 · Newegg $574 · Walmart $599
                     → one product, best offer = Newegg $574
```

Products are identified by a **fingerprint** (`tools/product_fingerprint.py`) that
prefers real global identifiers, most-trusted first:

```
GTIN  >  UPC  >  MPN (field)  >  MPN (parsed from title, e.g. CFI-7119)
      >  Google product_id  >  brand + model + variant (text)
```

So the same product from different retailers collapses even when Google assigns
different `product_id`s, as long as a shared manufacturer part number is present.
The MPN parser ignores spec-looking tokens (e.g. `DDR5-6000`, `8-Core`).
Unrealistic lowball prices are not chosen as the best offer when a realistic
alternative exists, and the alternatives are shown as "Also available at" in the
Discord embed.

> SerpAPI's shopping results don't expose explicit `gtin`/`upc`/`mpn` fields on
> this key, so those are read when present and the MPN is otherwise parsed from
> the title; the fingerprint accepts explicit identifier fields for when a richer
> data source is added.

## Retailer Trust Engine

`tools/retailer_trust.py` classifies every store into a trust tier and caps how
good a deal can look, so a cheap-but-sketchy listing can't outrank a trustworthy
one (Best Buy $579 beats RandomShop123 $549):

| Tier | Examples | Deal-score cap | Confidence cap |
|------|----------|---------------:|---------------:|
| 1 Preferred / first-party | Amazon, Best Buy, Walmart, Target, Costco, Newegg, Micro Center, B&H, GameStop, Sony, Nintendo, Apple | 1.00 | 1.00 |
| 2 Known specialty | AAAWave, Antonline, Adorama, MemoryC, Provantage | 0.90 | 0.85 |
| 3 Marketplace | eBay, AliExpress, Mercari, Temu, `Store - Seller` | 0.65 | 0.50 |
| 4 Unknown | any never-seen store | 0.45 | 0.30 |

- An **unknown store can never show "Amazing Deal"** — `rating_label()` returns
  `⚠️ Needs Verification` (Tier 4) or `🟡 Potential Deal` (Tier 3); "🔥 Amazing
  Deal" is reserved for Tier 1.
- **URL tracking is stripped** (`strip_tracking`) — `utm_*`, `gclid`, `fbclid`,
  `srsltid`, `ref`, `tag`, `aff`, etc. are removed before a link is posted.
- **Structural URL verification** (`is_valid_product_url`) flags links that are a
  homepage, a search page, non-HTTPS, or Google; the deal shows an "Unverified
  link" note. (A live HTTP-200 check is intentionally skipped because major
  retailers bot-block automated requests and would cause false rejections.)

## Deal scoring (false-positive reduction)

Deals are ranked by `tools/deal_scoring.py`, which combines several signals into a
`deal_score` (0–1) and a `confidence_score` (0–1), and returns human-readable
`reasons` (surfaced in the Discord embed and console):

- **Unrealistic prices** — a price far below the market average (median of the
  result set) or the last-seen price is flagged as likely fake/error instead of
  an "amazing deal" (e.g. a "$28 PS5 Pro" sinks to the bottom).
- **Seller reputation** — third-party marketplace sellers (the `Store - Seller`
  pattern, eBay, AliExpress, etc.) are penalized.
- **First-party preference** — Amazon, Walmart, Best Buy, Target, Costco, Newegg,
  Micro Center, and B&H are boosted.
- **Accessories / non-main-product listings** are ignored (controllers, cases,
  docks, chargers, …) unless the listing is the actual product.
- **Condition** — refurbished / open-box / used / parts-only / damaged listings
  are penalized unless the query explicitly asks for that condition.

The `DealResult.score_reasons` list explains why a deal ranked highly.

## Direct retailer links

Deal alerts link **straight to the retailer's product page** (Amazon, Best Buy,
Walmart, Target, Costco, Newegg, etc.) — never a Google Shopping search URL.

- SerpAPI's basic Google Shopping results only expose a Google Shopping
  `product_link`. The direct retailer URL is resolved via SerpAPI's
  `google_immersive_product` API (`tools/retailer_url.py`), which returns each
  store's real product link.
- To keep API usage low, the direct product URL is resolved for the **deal that
  actually gets posted** (one immersive lookup per watchlist item). Other deals
  carry the retailer's homepage as a non-Google fallback.
- If a direct product URL can't be found, the retailer's official website is used
  instead of Google Shopping (see `RETAILER_HOMEPAGES`).
- The direct URL is stored on the deal object (`DealResult.retailer_url`) and the
  Discord embed's **"Buy Now"** button links to it.
