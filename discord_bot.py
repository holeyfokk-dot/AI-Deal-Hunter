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


def start_bot():
    client.run(DISCORD_TOKEN)


def start_bot_thread():
    thread = threading.Thread(
        target=start_bot,
        daemon=True
    )
    thread.start()
    return thread