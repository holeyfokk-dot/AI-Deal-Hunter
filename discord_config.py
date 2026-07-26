from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

if not DISCORD_TOKEN:
    raise ValueError(
        "DISCORD_TOKEN is not set. Add it to your .env file "
        "(see .env.example)."
    )

if CHANNEL_ID == 0:
    raise ValueError(
        "CHANNEL_ID is not set. Add it to your .env file "
        "(see .env.example)."
    )
