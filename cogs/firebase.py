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
ref = db.reference(f"Users/307946608149135361")
ref.update({"steam_id": "76561198342056792"})

ref = db.reference(f"Guilds/853516997747933225")
ref.update({"news_channel": "891028959041585162"})


def set_guild(guild_id, channel_id):
    ref = db.reference(f"Guilds/{guild_id}")
    ref.update({"news_channel": channel_id})
