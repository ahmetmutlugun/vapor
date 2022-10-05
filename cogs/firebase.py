import os
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Fetch the service account key JSON file contents
cred = credentials.Certificate(os.getcwd() + "/keys/firebase.json")

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://vapor-d332f-default-rtdb.firebaseio.com/'
})


# As an admin, the app has access to read and write all data, regradless of Security Rules


def set_guild(guild_id, channel_id):
    ref = db.reference(f"Guilds/{guild_id}")
    ref.update({"news_channel": channel_id})


def get_news_channel(guild_id):
    ref = db.reference(f"Guilds/{guild_id}/")
    channel = ref.get("news_channel")
    if channel is not None:
        return channel[0]["news_channel"]
    return channel


def set_steam_id(discord_id, steam_id):
    ref = db.reference(f"Users/{discord_id}")
    ref.update({"steam_id": steam_id})


def get_steam_id(discord_id):
    ref = db.reference(f"Users/{discord_id}")
    steam_id = ref.get("steam_id")
    if steam_id is not None:
        return steam_id[0]["steam_id"]
    return steam_id
