import asyncio
import threading
import discord

from discord_config import DISCORD_TOKEN, CHANNEL_ID

intents = discord.Intents.default()
client = discord.Client(intents=intents)

bot_loop = None


@client.event
async def on_ready():
    global bot_loop
    bot_loop = asyncio.get_running_loop()

    print(f"✅ Logged in as {client.user}")

    channel = client.get_channel(CHANNEL_ID)

    if channel:
        await channel.send("🚀 AI Deal Hunter is online!")
        print("✅ Startup message sent!")
    else:
        print("❌ Channel not found")


async def _send(message):
    await client.wait_until_ready()

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("❌ Channel not found")
        return

    await channel.send(message)
    print("✅ Deal notification sent!")


def send_message(message):
    global bot_loop

    if bot_loop is None:
        print("❌ Bot loop not ready")
        return

    future = asyncio.run_coroutine_threadsafe(
        _send(message),
        bot_loop
    )

    try:
        future.result(timeout=10)
    except Exception as e:
        print(f"❌ Discord error: {e}")


def _build_deal_embed(deal, ai_rating="", price_note=""):
    product_name = deal.get("product_name", "Unknown")
    price = deal.get("current_price")
    store = deal.get("store", "Unknown")
    retailer_url = deal.get("retailer_url") or deal.get("url") or ""

    embed = discord.Embed(
        title=f"🔥 {product_name}",
        description=f"Deal found at **{store}**",
        color=0x2ECC71,
    )

    if isinstance(price, (int, float)):
        embed.add_field(name="💰 Price", value=f"${price:.2f}", inline=True)
    embed.add_field(name="🏪 Store", value=store, inline=True)

    if ai_rating:
        embed.add_field(name="🤖 AI Rating", value=ai_rating, inline=True)

    deal_score = deal.get("deal_score")
    if deal_score is not None:
        embed.add_field(name="📊 Deal Score", value=str(deal_score), inline=True)

    if price_note:
        embed.add_field(name="📈 Price Trend", value=price_note, inline=False)

    if retailer_url:
        embed.add_field(name="🔗 Product Page", value=retailer_url, inline=False)

    return embed, retailer_url, store


async def _send_deal(deal, ai_rating="", price_note=""):
    await client.wait_until_ready()

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("❌ Channel not found")
        return

    embed, retailer_url, store = _build_deal_embed(deal, ai_rating, price_note)

    view = discord.ui.View()
    # Only link buttons with a valid http(s) URL are allowed by Discord, and we
    # never post Google Shopping URLs.
    if isinstance(retailer_url, str) and retailer_url.startswith(("http://", "https://")):
        view.add_item(
            discord.ui.Button(
                label=f"🛒 Buy Now at {store}",
                style=discord.ButtonStyle.link,
                url=retailer_url,
            )
        )

    await channel.send(embed=embed, view=view)
    print("✅ Deal notification sent!")


def send_deal(deal, ai_rating="", price_note=""):
    """Post a rich deal embed with a 'Buy Now' button linking to the retailer."""
    global bot_loop

    if bot_loop is None:
        print("❌ Bot loop not ready")
        return

    future = asyncio.run_coroutine_threadsafe(
        _send_deal(deal, ai_rating, price_note),
        bot_loop,
    )

    try:
        future.result(timeout=10)
    except Exception as e:
        print(f"❌ Discord error: {e}")


def start_bot():
    client.run(DISCORD_TOKEN)


def start_bot_thread():
    thread = threading.Thread(
        target=start_bot,
        daemon=True
    )
    thread.start()
    return thread