import discord
from discord_config import DISCORD_TOKEN, CHANNEL_ID

intents = discord.Intents.default()
client = discord.Client(intents=intents)


async def send_message(message):
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("❌ Channel not found!")
        return

    await channel.send(message)
    print("✅ Message sent!")


@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

    # Import here to avoid a circular import
    import app

    # Close the bot after app finishes
    await client.close()


client.run(DISCORD_TOKEN)