import asyncio
import json
import logging
import re
from abc import ABC

from discord.ext import tasks
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions

from helpers import get_news, get_valid_steam_id, get_player_ban, exec_query, get_player_friends, get_player_profile, \
    query_steam_id, get_user_id
from inventory import Inventory

# TODO
# Respond with the linked profile to /getid and /setid
# Add user profile command to display profile embeds

logging.basicConfig(level=logging.INFO)
logging.info("Running Script...")
# client = commands.AutoShardedBot(description="Bringing Steam features as a Discord bot.")
NEWS_CHANNEL = 825110522922926144
guilds = []


class Vapor(commands.AutoShardedBot, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Start the task to run in the background
        self.refresh_news.start()
        self.client = self

    @tasks.loop(minutes=30)
    async def refresh_news(self):
        await self.wait_until_ready()
        channel = self.get_channel(825110522922926144)
        # Read existing articles from news.json
        with open('news.json', 'r') as json_file:
            try:
                old_news = json.dumps(json.load(json_file), sort_keys=True)
            except Exception:  # Too broad
                old_news = ""

        # Send request to news API
        updated_news = json.dumps(get_news(), sort_keys=True)

        # If the old news isn't the same as the new news update the news.json file

        if old_news != updated_news:
            with open('news.json', 'w') as outfile:
                outfile.write(updated_news)

        await channel.send(embed=front_page_embed())


client = Vapor(description="Bringing Steam features as a Discord bot.")


@client.event
async def on_ready():
    logging.info(f"Logged in as {client.user} (Discord ID: {client.user.id})")
    for guild in client.guilds:
        guilds.append(guild)


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
        embed = discord.Embed(title="CSGO News", type='rich', color=0x0c0c28, url=art['url'].replace(" ", ""))
        embed.add_field(name=art['title'], value=html_tags.sub('', art['contents']))
        contents.append(embed)
    pages = 5
    cur_page = 1
    message = await ctx.send(embed=contents[cur_page - 1])
    # Getting the message object for editing and reacting

    await message.add_reaction("◀️")
    await message.add_reaction("▶️")

    def check(reaction_emoji, user_name):
        return user_name == ctx.author and str(reaction_emoji.emoji) in ["◀️", "▶️"]
        # This makes sure nobody except the command sender can interact with the "menu"

    while True:
        try:
            reaction, user = await client.wait_for("reaction_add", timeout=60, check=check)
            # waiting for a reaction to be added - times out after x seconds, 60 in this
            # example

            if str(reaction.emoji) == "▶️" and cur_page != pages:
                cur_page += 1
                await message.edit(embed=contents[cur_page - 1])
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and cur_page > 1:
                cur_page -= 1
                await message.edit(embed=contents[cur_page - 1])
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
    steam_id = query_steam_id(ctx.author.id)
    if steam_id is None:
        await ctx.respond("Please use /setid to set your Steam ID!")
        return
    await ctx.respond(f"Your steam ID is: {steam_id}")


@has_permissions(administrator=True)
@client.slash_command(name="setchannel")
async def set_channel(ctx, channelid):
    global NEWS_CHANNEL
    NEWS_CHANNEL = channelid
    await ctx.respond(f"News channel has been set to {channelid}")


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
    embed.add_field(name=front_page['title'], value=html_tags.sub('', articles[0]['contents']))

    return embed


@client.slash_command(name="profile")
async def profile(ctx, steam_id=""):
    if steam_id == "":
        steam_id = query_steam_id(ctx.author.id)
        if steam_id is None:
            await ctx.respond("Please provide a Steam ID or use /setid.")
            return
    possible_id = get_user_id(steam_id)
    if possible_id is not None:
        steam_id = possible_id

    ban_data = get_player_ban(steam_id)
    data = get_player_profile(steam_id)
    friends = get_player_friends(steam_id)

    if data is None:
        await ctx.respond("Could not find a player with that name or ID!")
        return
    embed = discord.Embed(title=f"Profile of {data['personaname']}", type='rich',
                          color=0x0c0c28, url=data['profileurl'])

    friend_ids = []
    for key in friends.keys():
        friend_ids.append(key)
    friend_ids = friend_ids[0:3]
    friend_text: str = ""
    for i in friend_ids:
        friend = get_player_profile(i)
        friend_text += f"{friend['personaname']}, <t:{friends[i]}:D>\n"
    embed.add_field(name="Friends, Friends Since", value=friend_text)
    try:
        embed.add_field(name="Last Online", value=f"<t:{data['lastlogoff']}:f>")
    except KeyError:
        embed.add_field(name="Private", value="This profile is private!")
    embed.set_author(name=data['personaname'], icon_url=data['avatar'], url=data['profileurl'])
    embed.add_field(name="Bans",
                    value=f"VAC Ban: {ban_data['VACBanned']}\nDays since last ban: {ban_data['DaysSinceLastBan']}\nEconomy Ban: {ban_data['EconomyBan']}\nCommunity Ban: {ban_data['CommunityBanned']}",
                    inline=True)
    embed.add_field(name="Real name", value=data['realname'], inline=True)
    await ctx.respond(embed=embed)


@client.slash_command(name="help")
async def help_(ctx):
    embed = discord.Embed(title="Help Information", type="rich", color=0x0c0c28,
                          url="https://github.com/ahmetmutlugun/vapor")
    embed.add_field(name="ping", value="Displays the bot's ping.")
    embed.add_field(name="csnews", value="Shows the latest CS:GO news.")
    embed.add_field(name="setid", value="Links steam account.")
    embed.add_field(name="getid", value="Shows the linked steam account.")
    embed.add_field(name="profile", value="Displays profile and ban information.")
    embed.add_field(name="inventory", value="Calculate CS:GO inventory value.")
    embed.add_field(name="item", value="Shows the price of the selected item.")
    await ctx.respond(embed=embed)


file = open("keys/discord.key", "r")
token = file.read()
file.close()
client.add_cog(Inventory(client))
client.run(token)
