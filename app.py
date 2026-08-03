from ai import matches_search
from config import logger
from manager import AgentManager
from watchlist import load_watchlist
from price_history import load_prices, has_price_changed
from discord_bot import send_deal
from tools.retailer_trust import rating_label, trust_stars
from tools.retailer_url import fetch_direct_url, is_valid_product_url
from tools.product_page_verify import (
    MISMATCH,
    OUT_OF_STOCK,
    UNVERIFIED,
    VERIFIED,
    PageVerification,
    verify_product_page,
)


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

        lowest_price = min(price for price, _ in matching)

        # Behaviorally verify candidates (best-first) before posting: fetch the
        # page and confirm it actually sells the searched product. Reject
        # mismatches / out-of-stock; fall back to an unverifiable-but-structural
        # link only if nothing verifies.
        ranked = [deal for _, deal in sorted(matching, key=lambda pair: pair[1].get("deal_score", 0), reverse=True)]

        best = None
        direct_url = None
        verification = None
        fallback = None  # (deal, url, PageVerification) for a bot-blocked page
        for candidate in ranked[:3]:
            url = resolve_direct_url(candidate)
            if not is_valid_product_url(url):
                result = PageVerification(UNVERIFIED, reason="Link is a homepage / not a product page")
            else:
                result = verify_product_page(url, search, want_out_of_stock=False)

            if result.status == VERIFIED:
                best, direct_url, verification = candidate, url, result
                break
            if result.status in (MISMATCH, OUT_OF_STOCK):
                print(f"   ✗ Rejected {candidate.get('store')}: {result.reason}")
                continue
            if fallback is None:
                fallback = (candidate, url, result)

        if best is None and fallback is not None:
            best, direct_url, verification = fallback

        if best is None:
            print("No verified product page found for this search.\n")
            continue

        best["retailer_url"] = direct_url
        best["url"] = direct_url
        verified = verification.status == VERIFIED
        best_price = get_price(best)
        product_name = best.get("product_name", "Unknown")

        best.setdefault("metadata", {})
        best["metadata"]["verification"] = verification.status
        if verification.identifiers:
            best["metadata"]["verified_identifiers"] = verification.identifiers
        stars = trust_stars(best.get("store"), verification.status)
        best["metadata"]["trust_stars"] = stars

        if verified:
            best.setdefault("score_reasons", []).insert(0, f"[+] Verified product page - {verification.reason}")
        else:
            best.setdefault("score_reasons", []).append(f"[warn] {verification.reason} - verify before buying")

        old_price = load_prices().get(product_name)
        changed = has_price_changed(product_name, best_price)

        # Trust-aware rating: untrusted sellers never show "Amazing Deal".
        ai_rating = rating_label(best.get("deal_score", 0.0), best.get("store"))

        print("\n🏆 BEST DEAL")
        print("-" * 60)
        print(f"🎮 Product: {product_name}")
        print(f"💰 Price: ${best_price:.2f}")
        print(f"🏬 Store: {best.get('store', 'Unknown')}  {stars}")
        print(f"🤖 AI Rating: {ai_rating}")
        print(f"📊 Deal Score: {best.get('deal_score')}  🎯 Confidence: {best.get('confidence_score')}")
        print(f"🔗 Direct link: {direct_url}")
        print(f"   {'✅ Verified: ' + (verification.title or '')[:60] if verified else '⚠️ ' + verification.reason}")

        for reason in best.get("score_reasons", []):
            print(f"   • {reason}")

        other_offers = (best.get("metadata") or {}).get("other_offers") or []
        if other_offers:
            print("   🛍️ Also available at:")
            for offer in other_offers[:5]:
                price_val = offer.get("price")
                if isinstance(price_val, (int, float)):
                    print(f"      - {offer.get('store', 'Unknown')}: ${price_val:.2f}")

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
            print(f"🤖 AI Rating: {rating_label(item.get('deal_score', 0.0), item.get('store'))}")
            print(f"🔗 Link: {item.get('retailer_url') or item.get('url') or 'No link'}")
            print("-" * 60)

            shown += 1

            if shown == 10:
                break

    print("\n✅ Watchlist scan complete.")


if __name__ == "__main__":
    run()
