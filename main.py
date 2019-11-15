import json
import os
import threading

from dotenv import load_dotenv
from rx.subject import Subject

from discord_client import DiscordClient
from fb_client import FBClient

load_dotenv()

# FB Bot
try:
    # Load the session cookies
    with open("secrets/session.json", "r") as f:
        cookies = json.load(f)
except:
    # If it fails, never mind, we'll just login again
    pass

# RxPy Subject for pushing information from FB Bot to Discord Bot
source = Subject()

fb_client: FBClient = FBClient(os.getenv("FB_USERNAME"), os.getenv("FB_PASSWORD"), source, session_cookies=cookies)

# Must start FB Bot on separate thread, since both fb_client.listen and discord_client.run block.
thread = threading.Thread(target=fb_client.listen)
thread.start()

# Discord Bot
discord_client: DiscordClient = DiscordClient(fb_client, source)

token = os.getenv("DISCORD_TOKEN")

# Discord Bot is run on main thread.
discord_client.run(token)
