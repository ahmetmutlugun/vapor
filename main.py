import requests
import discord
import json
from discord.ext import commands
import re
import os
import logging
import psycopg2
import asyncio

#TODO
# Make docker-compose faster
# Use steam id from the database when running /banstatus
# Display more information in the ban status embed
# Include URL to the news website for csnews when filtering out html tags
# Respond with the linked profile to /getid and /setid
# Add user profile command to display profile embeds
# Find and implement API for inventory valuation

logging.info("Running Script...")
client = commands.Bot(description="Bringing Steam features as a Discord bot.")

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
    # To get csgo news use app id 730
    articles = get_news(count=5, appid=730)
    contents = []
    html_tags = re.compile(r'<[^>]+>')
    for art in articles:
        # Create the embed for each page; 1 per article
        embed = discord.Embed(title=f"CSGO News", type='rich', color=0x0c0c28, url=art['url'].replaceAll(" ", ""))
        embed.add_field(name=art['title'], value=html_tags.sub('', art['contents']))
    pages = 5
    cur_page = 1
    message = await ctx.send(contents[cur_page-1])
    # getting the message object for editing and reacting

    await message.add_reaction("◀️")
    await message.add_reaction("▶️")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]
        # This makes sure nobody except the command sender can interact with the "menu"

    while True:
        try:
            reaction, user = await client.wait_for("reaction_add", timeout=60, check=check)
            # waiting for a reaction to be added - times out after x seconds, 60 in this
            # example

            if str(reaction.emoji) == "▶️" and cur_page != pages:
                cur_page += 1
                await message.edit(content=contents[cur_page-1])
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and cur_page > 1:
                cur_page -= 1
                await message.edit(content=f"Page {cur_page}/{pages}:\n{contents[cur_page-1]}")
                await message.remove_reaction(reaction, user)

            else:
                await message.remove_reaction(reaction, user)
                # removes reactions if the user tries to go forward on the last page or
                # backwards on the first page
        except asyncio.TimeoutError:
            await message.delete()
            break
            # ending the loop if user doesn't react after x seconds


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


def get_player_ban(steam_id):
    r = requests.get(
        f' http://api.steampowered.com/ISteamUser/GetPlayerBans/v1',
        params={"key": steam_key, "steamids": f"{steam_id}"},
        headers=headers)
    data = json.loads(r.content.decode('utf-8'))
    if len(data['players']) < 1:
        return None
    return data["players"][0]


def get_news(count: int, appid: int):
    r = requests.get(
        f' https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={appid}&count={count}&maxlength=30000'
        f'&format=json',
        headers=headers)
    return r.json()['appnews']['newsitems']


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



file = open("keys/discord.key", "r")
token = file.read()
file.close()
client.run(token)
