#!/home/zouzou/tools/venv/bin/python
import sys
import os
import asyncio
import discord
from dotenv import load_dotenv

# On force le chargement du .env qui est dans le dossier tools
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

CHANNELS = {
    'galery': 1501216807447560284, 
    'database': 1501216853769453752,
    'control': 1501216354446086274
}

async def notify(channel_key, message, file_path=None):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        channel = client.get_channel(CHANNELS.get(channel_key))
        if channel:
            file = discord.File(file_path) if file_path and os.path.exists(file_path) else None
            await channel.send(content=message, file=file)
        await client.close()
    
    await client.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    # Usage: ./send_discord.py gallery "Message" "chemin/image.png"
    chan = sys.argv[1]
    msg = sys.argv[2]
    img = sys.argv[3] if len(sys.argv) > 3 else None
    asyncio.run(notify(chan, msg, img))