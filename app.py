from ai import score_deal, matches_search
from config import logger
from manager import AgentManager
from watchlist import load_watchlist
from price_history import load_prices, has_price_changed
from discord_bot import send_message


def get_price(item):
    try:
        return float(
            str(item.get("price", "0"))
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

        shopping_results = get_search_results(agent_manager, search)

        if not shopping_results:
            print("No products found.\n")
            continue

        shopping_results = sorted(shopping_results, key=get_price)

        prices = []

        for item in shopping_results:
            price = get_price(item)

            if price != float("inf"):
                prices.append(price)

        if not prices:
            print("No valid prices.\n")
            continue

        lowest_price = min(prices)

        best = None

        for item in shopping_results:

            if matches_search(search, item.get("title", "")) == 0:
                continue

            best = item
            break

        if best is None:
            print("No matching products found.\n")
            continue

        best_price = get_price(best)
        product_name = best.get("title", "Unknown")

        prices_history = load_prices()
        old_price = prices_history.get(product_name)
        changed = has_price_changed(product_name, best_price)

        print("\n🏆 BEST DEAL")
        print("-" * 60)
        print(f"🎮 Product: {product_name}")
        print(f"💰 Price: ${best_price:.2f}")
        print(f"🏬 Store: {best.get('source', 'Unknown')}")
        print(f"🤖 AI Rating: {score_deal(best_price)}")

        if old_price is None:
            print("🆕 First time seeing this product")

        elif changed:

            difference = old_price - best_price

            if difference > 0:
                print(f"📉 Price dropped ${difference:.2f}")

            elif difference < 0:
                print(f"📈 Price increased ${abs(difference):.2f}")

        else:
            print("✅ Price unchanged")

        message = f"""🔥 **{search} Deal Found!**

🎮 Product: {product_name}
💰 Price: ${best_price:.2f}
🏪 Store: {best.get('source', 'Unknown')}
🤖 AI Rating: {score_deal(best_price)}
🔗 🔗 Link: {best.get('product_link', 'No link')}
"""

        print("📤 Sending Discord notification...")
        send_message(message)

        print("\nTop Results")
        print("-" * 60)

        shown = 0

        for item in shopping_results:

            if matches_search(search, item.get("title", "")) == 0:
                continue

            price = get_price(item)

            print(f"🎮 Product: {item.get('title')}")
            print(f"💰 Price: ${price:.2f}")
            print(f"💸 ${price - lowest_price:.2f} above cheapest")
            print(f"🏬 Store: {item.get('source', 'Unknown')}")
            print(f"🤖 AI Rating: {score_deal(price)}")
            print(f"🔗 Link: {item.get('product_link', 'No link')}")
            print("-" * 60)

            shown += 1

            if shown == 10:
                break

    print("\n✅ Watchlist scan complete.")


if __name__ == "__main__":
    run()