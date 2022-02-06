import logging
import re
import discord
from discord.ext import commands
from helpers import *
from inventory import Inventory

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

guilds = []


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


file = open("keys/discord.key", "r")
token = file.read()
file.close()
client.add_cog(Inventory(client))
client.run(token)
