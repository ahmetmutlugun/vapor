import asyncio
import json
import logging
import re
import discord
from discord.ext import commands, tasks

from helpers import *
from inventory import Inventory

# TODO
# Use steam id from the database when running /banstatus
# Display more information in the ban status embed
# Respond with the linked profile to /getid and /setid
# Add user profile command to display profile embeds

logging.info("Running Script...")
client = commands.AutoShardedBot(description="Bringing Steam features as a Discord bot.")
NEWS_CHANNEL = 853516997747933225853517404218982420
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


@client.slash_command(name='ping')
async def ping(ctx):
    await ctx.respond(f"My ping is: {round(client.latency * 1000)}ms")


@client.slash_command(name="csnews", guilds_ids=guilds)
async def cs_news(ctx):
    # Get the news from the news.json file which is updated every hour
    with open('news.json', 'r') as f:
         articles = json.load(f)
    contents = []
    html_tags = re.compile(r'<[^>]+>')
    for art in articles:
        # Create the embed for each page; 1 per article
        embed = discord.Embed(title=f"CSGO News", type='rich', color=0x0c0c28, url=art['url'].replace(" ", ""))
        embed.add_field(name=art['title'], value=html_tags.sub('', art['contents']))
        contents.append(embed)
    pages = 5
    cur_page = 1
    message = await ctx.send(contents[cur_page - 1])
    # Getting the message object for editing and reacting

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
                await message.edit(content=contents[cur_page - 1])
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and cur_page > 1:
                cur_page -= 1
                await message.edit(content=f"Page {cur_page}/{pages}:\n{contents[cur_page - 1]}")
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


@has_permissions(kick_member=True)
@client.slash_command(name="setchannel")
async def set_channel(ctx, channelid):
    global NEWS_CHANNEL
    NEWS_CHANNEL = channelid


@client.slash_command(name="news")
async def game_news(ctx, game_code):

    # If the person needs help return an embed of all the supported codes = CSGO
    if isinstance(game_code, str) and game_code == "help":
        help = discord.Embed(title="Supported game news", color=0x0000FF)
        help.add_field(name="CSGO", value=f"Game code: {730}", inline=True).set_image("https://static-cdn.jtvnw.net/ttv-boxart/32399-285x380.jpg")
        # TODO: add other games




@tasks.loop(minutes=60)
async def refresh_news():

    # Read existing articles from news.json
    with open('news.json', 'r') as json_file:
        try:
            old_news = json.dumps(json.load(json_file), sort_keys=True)
        except Exception:
            old_news = ""


    # Send request to news API
    updated_news = json.dumps(get_news(), sort_keys=True)

    # If the old news isn't the same as the new news update the news.json file
    chan = client.get_channel(NEWS_CHANNEL).r
    if old_news != updated_news:
        with open('news.json', 'w') as outfile:
            outfile.write(updated_news)

        channel = client.get_channel(NEWS_CHANNEL)
        await channel.send(front_page_embed())


def front_page_embed():
    """
    Creates an embed of the front page of the news
    :return: the Discord Embed
    """
    with open('news.json', 'r') as f:
        articles = json.load(f)

    front_page = articles[0]
    contents = []
    html_tags = re.compile(r'<[^>]+>')
    embed = discord.Embed(title=f"CSGO News", type='rich', color=0x0c0c28, url=front_page['url'].replace(" ", ""))
    embed.add_field(name=front_page['title'], value=html_tags.sub('', art['contents']))

    return embed


file = open("keys/discord.key", "r")
token = file.read()
file.close()
client.add_cog(Inventory(client))
client.run(token)
