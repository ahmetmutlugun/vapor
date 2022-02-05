import asyncio

import requests
import discord
import json
from discord.ext import commands
import re
import os
import logging
import psycopg2

# TODO
# Make docker-compose faster
# Use steam id from the database when running /banstatus
# Display more information in the ban status embed
# Include URL to the news website for csnews when filtering out html tags
# Respond with the linked profile to /getid and /setid
# Add user profile command to display profile embeds
# Optimize inventory

logging.info("Running Script...")
client = commands.AutoShardedBot(description="Bringing Steam features as a Discord bot.")

headers = {'Accept': 'application/json'}
guilds = []

file2 = open("keys/steam.key", "r")
steam_key = file2.read()
file2.close()


@client.event
async def on_ready():
    logging.info(f"Logged in as {client.user} (Discord ID: {client.user.id})")
    for guild in client.guilds:
        guilds.append(guild)


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
    steam_id = get_valid_steam_id(steam_id)
    if steam_id is None:
        await ctx.respond("Please use a valid steam ID or custom url.")
        return
    res = exec_query("SELECT * FROM steam_data WHERE discord_id=(%s)", (author_id,))
    # If a row doesn't exist for a user insert into the table
    if not res:
        exec_query("INSERT INTO steam_data (discord_id, steam_id) VALUES (%s, %s)", (author_id, steam_id))
    # If a row does exist for a user update the steam_id for the discord user
    else:
        exec_query("UPDATE steam_data SET steam_id=(%s) WHERE discord_id=(%s)", (steam_id, author_id))

    await ctx.respond(f"Steam Account {steam_id} successfully linked!")


@client.slash_command(name="getid")
async def get_id(ctx):
    user_id_response = exec_query("SELECT steam_id FROM steam_data WHERE discord_id=(%s)", (str(ctx.author.id),))
    if user_id_response:
        await ctx.respond(f"Your steam ID is: {user_id_response[0][0]}")
        return
    await ctx.respond(f"Please use /setid to set your Steam ID!")


@client.slash_command(name="inventory")
async def get_inventory(ctx, steam_id=None):
    if steam_id is None:
        user_id_response = exec_query("SELECT steam_id FROM steam_data WHERE discord_id=(%s)", (str(ctx.author.id),))
        if user_id_response:
            steam_id = user_id_response[0][0]
    await ctx.respond(f"Calculating inventory value for {steam_id}. This might take a few minutes.", )
    r = requests.get(f"https://steamcommunity.com/inventory/{steam_id}/730/2?l=english&count=5000",
                     headers=headers)
    assets = r.json()

    value = await calc_inventory_value(assets)
    await ctx.respond(f"Inventory value of {steam_id} is ${value}")


async def calc_inventory_value(assets):

    id_dictionary = {}
    for i in assets['assets']:
        if i['classid'] in id_dictionary:
            id_dictionary.update({i['classid']: id_dictionary[i['classid']] + 1})
        else:
            id_dictionary.update({i['classid']: 1})
    asset_list = []
    for i in assets['descriptions']:
        for _ in range(0, id_dictionary[i['classid']]):
            asset_list.append(i['market_hash_name'])

    total: float = 0
    for i in asset_list:
        total += item_value(i)
    return round(total, 2)


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


def exec_query(query_string: str, params: tuple):
    res = []
    # Establish a session with the postgres database
    with psycopg2.connect(
            host=os.environ["HOST"],
            database=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"]
    ) as conn:
        # Create a cursor
        with conn.cursor() as cur:
            # Execute query with parameters
            cur.execute(query_string, params)
            try:
                res = cur.fetchall()
            except psycopg2.ProgrammingError:
                res = []
    # Return all the results
    return res


def get_valid_steam_id(steam_id):
    if get_player_ban(steam_id) is not None:
        return steam_id
    steam_url = get_user_id(steam_id)
    if steam_url is not None:
        return steam_url
    return None


def item_value(item: str):
    r = requests.get(
        f'http://csgobackpack.net/api/GetItemPrice/?currency=USD&id={item}&time=7&icon=1',
        headers=headers, params={'id': item.replace(' ', '%20')})

    try:
        price = float(r.json()['median_price'])
    except KeyError:
        return 0
    return price


file = open("keys/discord.key", "r")
token = file.read()
file.close()
client.run(token)
