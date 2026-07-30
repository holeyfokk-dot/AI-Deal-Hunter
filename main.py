import time

from app import run
from discord_bot import start_bot_thread

print("=" * 60)
print("🤖 AI Deal Hunter")
print("=" * 60)

print("🚀 Starting Discord bot...")
start_bot_thread()

print("⏳ Waiting for Discord to connect...")
time.sleep(3)

print("✅ Starting Deal Hunter...\n")

run()

print("\n🏁 AI Deal Hunter finished.")