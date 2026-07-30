from ai import score_deal, matches_search
from config import logger
from manager import AgentManager
from watchlist import load_watchlist
from price_history import load_prices, has_price_changed
from discord_bot import send_deal
from tools.retailer_url import fetch_direct_url


def get_price(deal):
    try:
        return float(
            str(deal.get("current_price", deal.get("price", "inf")))
            .replace("$", "")
            .replace(",", "")
        )
    except Exception:
        return float("inf")


def get_search_results(agent_manager: AgentManager, query: str):
    responses = agent_manager.route("search", {"query": query})

    results = []

    for response in responses:
        payload = response.get("response", {})
        if payload.get("deals") is not None:
            results.extend(payload.get("deals", []))
            continue
        results.extend(payload.get("shopping_results", []))

    return results


def resolve_direct_url(deal):
    """Upgrade a deal's URL to a direct retailer product page (never Google).

    Falls back to whatever non-Google URL the deal already carries (typically
    the retailer's homepage) when a direct product link can't be resolved.
    """
    current = deal.get("retailer_url") or deal.get("url")
    metadata = deal.get("metadata") or {}
    token = metadata.get("immersive_token")
    store = deal.get("store") or metadata.get("source")

    direct = fetch_direct_url(token, store)
    return direct or current


def run():
    agent_manager = AgentManager()
    agent_manager.startup_summary()

    watchlist = load_watchlist()

    location = input("ZIP code or city (press Enter to skip): ")

    logger.info("Scanning watchlist...")

    for search in watchlist:

        print("=" * 60)
        print(f"Searching: {search}")
        print("=" * 60)

        deals = get_search_results(agent_manager, search)

        if not deals:
            print("No products found.\n")
            continue

        matching = []

        for deal in deals:
            if not isinstance(deal, dict):
                continue

            if matches_search(search, deal.get("product_name", "")) == 0:
                continue

            price = get_price(deal)

            if price != float("inf"):
                matching.append((price, deal))

        if not matching:
            print("No matching products found.\n")
            continue

        matching.sort(key=lambda pair: pair[0])
        lowest_price = matching[0][0]

        best = max(matching, key=lambda pair: pair[1].get("deal_score", 0))[1]
        best_price = get_price(best)
        product_name = best.get("product_name", "Unknown")

        # Resolve the direct retailer product URL for the deal we post.
        direct_url = resolve_direct_url(best)
        best["retailer_url"] = direct_url
        best["url"] = direct_url

        old_price = load_prices().get(product_name)
        changed = has_price_changed(product_name, best_price)

        ai_rating = score_deal(best_price)

        print("\n🏆 BEST DEAL")
        print("-" * 60)
        print(f"🎮 Product: {product_name}")
        print(f"💰 Price: ${best_price:.2f}")
        print(f"🏬 Store: {best.get('store', 'Unknown')} ({best.get('store_reputation', 'unknown')})")
        print(f"🤖 AI Rating: {ai_rating}")
        print(f"📊 Deal Score: {best.get('deal_score')}  🎯 Confidence: {best.get('confidence_score')}")
        print(f"🔗 Direct link: {direct_url}")

        for reason in best.get("score_reasons", []):
            print(f"   • {reason}")

        price_note = ""

        if old_price is None:
            price_note = "🆕 First time seeing this product"
            print(price_note)
        elif changed:
            difference = old_price - best_price
            if difference > 0:
                price_note = f"📉 Price dropped ${difference:.2f}"
            elif difference < 0:
                price_note = f"📈 Price increased ${abs(difference):.2f}"
            if price_note:
                print(price_note)
        else:
            price_note = "✅ Price unchanged"
            print(price_note)

        print("📤 Sending Discord notification...")
        send_deal(best, ai_rating=ai_rating, price_note=price_note)

        print("\nTop Results")
        print("-" * 60)

        shown = 0

        for price, item in matching:
            print(f"🎮 Product: {item.get('product_name')}")
            print(f"💰 Price: ${price:.2f}")
            print(f"💸 ${price - lowest_price:.2f} above cheapest")
            print(f"🏬 Store: {item.get('store', 'Unknown')}")
            print(f"🤖 AI Rating: {score_deal(price)}")
            print(f"🔗 Link: {item.get('retailer_url') or item.get('url') or 'No link'}")
            print("-" * 60)

            shown += 1

            if shown == 10:
                break

    print("\n✅ Watchlist scan complete.")


if __name__ == "__main__":
    run()
