# Cinderella-Forwards Bot - vars.py
import os
from os import environ

API_ID   = int(environ.get("API_ID", "0"))
API_HASH = environ.get("API_HASH", "")
BOT_TOKEN = environ.get("BOT_TOKEN", "")

OWNER  = int(environ.get("OWNER", "0"))
CREDIT = environ.get("CREDIT", "💥 @CinderellaContactBot")

AUTH_USER  = os.environ.get("AUTH_USERS", str(OWNER)).split(",")
AUTH_USERS = [int(u) for u in AUTH_USER if u.strip()]
if OWNER and OWNER not in AUTH_USERS:
    AUTH_USERS.append(OWNER)

# Userbot session string (for private/restricted source channels)
# Generate via: python3 generate_session.py
SESSION_STRING = environ.get("SESSION_STRING", "")

# Forward delay between each file (seconds)
FORWARD_DELAY = int(environ.get("FORWARD_DELAY", "3"))
