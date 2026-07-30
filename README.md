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
