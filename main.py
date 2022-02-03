import requests
import discord
import json
from discord.ext import commands
import re
import os
import logging
import psycopg2

logging.log(20, "Running Script...")
client = commands.Bot(description="Bringing Steam features as a Discord bot.")

headers = {'Accept': 'application/json'}
guilds = []

file2 = open("keys/steam.key", "r")
steam_key = file2.read()
file2.close()

# Establish a session with the postgres database
conn = psycopg2.connect(
    host=os.environ["HOST"],
    database=os.environ["POSTGRES_DB"],
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"]
)


@client.event
async def on_ready():
    logging.log(20, f"Logged in as {client.user} (Discord ID: {client.user.id})")
    for guild in client.guilds:
        guilds.append(guild)


# TODO Display more information in the Embed
@client.slash_command(name="banstatus")
async def ban_status(ctx, steam_id):
    if steam_id is None:
        await ctx.respond("Please provide a Steam ID or custom URL!")
        return
    possible_id = get_user_id(steam_id)
    if possible_id is not None:
        data = get_player_ban(possible_id)
        url = f"http://steamcommunity.com/profiles/{possible_id}/"
    else:
        url = f"http://steamcommunity.com/profiles/{steam_id}/"
        data = get_player_ban(steam_id)

    if data is None:
        await ctx.respond("Could not find a player with that name or ID!")
        return
    embed = discord.Embed(title=f"Profile of {steam_id}", type='rich',
                          color=0x0c0c28, url=url)
    embed.add_field(name=f"VAC Banned?", value=data['VACBanned'])
    embed.add_field(name=f"Days Since Last Ban", value=data['DaysSinceLastBan'])

    await ctx.respond(embed=embed)


# TODO Include URL to the news website
@client.slash_command(name="csnews", guilds_ids=guilds)
async def cs_news(ctx):
    data = get_app_data()
    embed = discord.Embed(title=f"CSGO News", type='rich',
                          color=0x0c0c28, url="https://blog.counter-strike.net/")
    html_tags = re.compile(r'<[^>]+>')
    embed.add_field(name=f"{data['title']}", value=html_tags.sub('', data['contents']))
    await ctx.respond(embed=embed)


@client.slash_command(name="setid")
async def set_id(ctx, steam_id: str):
    author_id = str(ctx.author.id)
    cur = conn.cursor()
    cur.execute("SELECT * FROM steam_data WHERE discord_id=(%s)", (author_id,))
    res = cur.fetchall()
    # If a row doesn't exist for a user insert into the table
    if res is None:
        cur.execute("INSERT INTO steam_data (discord_id, steam_id) VALUES (%s, %s, %s)", (author_id, steam_id))
    # If a row does exist for a user update the steam_id for the discord user
    else:
        cur.execute("UPDATE steam_data SET steam_id=%s WHERE discord_id=%s", (author_id, steam_id))

    # Commit changes
    conn.commit()
    # Close the cursor
    cur.close()
    await ctx.respond(f"Steam Account {steam_id} successfully linked!")


@client.slash_command(name="getid")
async def get_id(ctx):
    cur = conn.cursor()
    cur.execute("SELECT steam_id FROM steam_data WHERE discord_id=(%s)", (str(ctx.author.id),))
    user_id_response = cur.fetchone()
    cur.close()
    if user_id_response is not None:
        await ctx.respond(f"Your steam ID is: {user_id_response[0]}")
    await ctx.respond(f"Please use /setid to set your Steam ID!")


def get_player_ban(steam_id):
    r = requests.get(
        f' http://api.steampowered.com/ISteamUser/GetPlayerBans/v1',
        params={"key": steam_key, "steamids": f"{steam_id}"},
        headers=headers)
    data = json.loads(r.content.decode('utf-8'))
    if len(data['players']) < 1:
        return None
    return data["players"][0]


def get_app_data():
    r = requests.get(
        f' http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid=730&count=1&maxlength=30000&format=json',
        headers=headers)
    data = r.json()
    return data['appnews']['newsitems'][0]


def get_user_id(name: str):
    r = requests.get(
        f'http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={steam_key}&vanityurl={name}',
        headers=headers)
    if r.json()['response']['success'] == 1:
        return r.json()['response']['steamid']
    return None


file = open("keys/discord.key", "r")
token = file.read()
file.close()
client.run(token)
