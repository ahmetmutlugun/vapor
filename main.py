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
NEWS_CHANNEL = 891028959041585162
guilds = []


class Vapor(commands.AutoShardedBot, ABC):
    """
    Custom AutoShardedBot to create loop commands
    """
    def __init__(self, *args, **kwargs):
        """
        Starts refresh_news
        :param args: args
        :param kwargs: kwargs
        """
        super().__init__(*args, **kwargs)

        # Start the task to run in the background
        self.refresh_news.start()
        self.client = self

    @tasks.loop(minutes=30)
    async def refresh_news(self):
        """
        Checks for new news every 30 minutes, and sends them to the news channel.
        """
        await self.wait_until_ready()
        channel = self.get_channel(891028959041585162)
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
    """
    Records guilds and status when the bot is ready
    :return:
    """
    logging.info(f"Logged in as {client.user} (Discord ID: {client.user.id})")
    for guild in client.guilds:
        guilds.append(guild)


@client.slash_command(name='ping', description="Displays latency.")
async def ping(ctx):
    """
    Sends ping in milliseconds
    :param ctx: Context
    """
    await ctx.respond(f"My ping is: {round(client.latency * 1000)}ms")


@client.slash_command(name="csnews", guilds_ids=guilds, description="Show the latest CS:GO news.")
async def cs_news(ctx):
    """
    Get the news from the news.json file which is updated every hour
    :param ctx: Context
    """
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


@client.slash_command(name="setid", description="Link a steam account to your account")
async def set_id(ctx, steam_id: str):
    """
    Sets steam_id to discord id in the database
    :param ctx: Context
    :param steam_id: Steam ID
    """
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


@client.slash_command(name="getid", description="Get saved steam account")
async def get_id(ctx):
    """
    Gets user's saved steam id and sends it as an embed
    :param ctx: Context
    """
    # Legacy code
    # steam_id = query_steam_id(ctx.author.id)
    # if steam_id is None:
    #     await ctx.respond("Please use /setid to set your Steam ID!")
    #     return
    # await ctx.respond(f"Your steam ID is: {steam_id}")

    if (i := generate_profile_embed(query_steam_id(ctx.author.id), ctx.author.id)) is not None:
        await ctx.respond(embed=i)
    else:
        await ctx.respond("Please use /setid to set your Steam ID!")


@has_permissions(administrator=True)
@client.slash_command(name="setchannel")
async def set_channel(ctx, channel_id):
    """
    Sets global news channel
    :param ctx:
    :param channel_id: discord channel id
    """
    global NEWS_CHANNEL
    NEWS_CHANNEL = channel_id
    await ctx.respond(f"News channel has been set to {channel_id}")


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
    embed.add_field(name=front_page['title'], value=str(html_tags.sub('', articles[0]['contents']))[0:1020]+"...")

    return embed


@client.slash_command(name="profile", description="Show the profile of a steam user.")
async def profile(ctx, steam_id=""):
    """
    Sends user profile as an embed from given or saved steam id
    :param ctx: Context
    :param steam_id: Steam ID
    """
    if (i := generate_profile_embed(steam_id, ctx.author.id)) is not None:
        await ctx.respond(embed=i)
    else:
        await ctx.respond("Please provide a Steam ID or use /setid.")


def generate_profile_embed(steam_id, author):
    """
    Generates profile embed from steam id.
    If steam id is not provided, author id is used to find a saved steam id
    :param steam_id: Steam ID
    :param author: Discord user id
    :return: Embed of user profile. None if an error occurs
    """
    if steam_id == "":
        steam_id = query_steam_id(author)
        if steam_id is None:
            return None
    possible_id = get_user_id(steam_id)
    if possible_id is not None:
        steam_id = possible_id

    ban_data = get_player_ban(steam_id)
    data = get_player_profile(steam_id)
    friends = get_player_friends(steam_id)

    if data is None:
        return None
    embed = discord.Embed(title=f"Profile of {data['personaname']}", type='rich',
                          color=0x0c0c28, url=data['profileurl'])

    if friends is not None:
        friend_ids = []
        for key in friends.keys():
            friend_ids.append(key)
        friend_ids = friend_ids[0:3]
        friend_text: str = ""
        try:
            for i in friend_ids:
                friend = get_player_profile(i)
                friend_text += f"{friend['personaname']}, <t:{friends[i]}:D>\n"
            if len(friend_text) > 3:
                embed.add_field(name="Friends, Friends Since", value=friend_text)
        except KeyError:
            embed.add_field(name="Friends, Friends Since", value="Friend list is private!")
    else:
        embed.add_field(name="Friends, Friends Since", value="Friend list is private!")

    try:
        embed.add_field(name="Last Online", value=f"<t:{data['lastlogoff']}:f>")
    except KeyError:
        embed.add_field(name="Private", value="This profile is private!")
    embed.set_author(name=data['personaname'], icon_url=data['avatar'], url=data['profileurl'])

    embed.add_field(name=chr(173), value=chr(173))
    embed.add_field(name="Bans", value=format_ban_text(ban_data))
    try:
        embed.add_field(name="Real name", value=data['realname'])
    except KeyError:
        embed.add_field(name="Real name", value="None")
    embed.add_field(name=chr(173), value=chr(173))
    return embed


def format_ban_text(ban_data):
    """
    Formats ban text from ban data gathered from the steam API
    :param ban_data: Steam API ban data
    :return: Bans formatted as a string
    """
    ban_text = ""
    if ban_data['VACBanned']:
        ban_text += f"VAC Ban: ⚠️\n"
    if int(ban_data['DaysSinceLastBan']) > 0:
        ban_text += f"Days since last ban: {ban_data['DaysSinceLastBan']}"
    if ban_data['EconomyBan'] != "none":
        ban_text += f"Economy Ban: ⚠️"
    if ban_data['CommunityBanned']:
        ban_text += f"Community Ban: ⚠️"
    if int(ban_data['NumberOfGameBans']) > 0:
        ban_text += f"Game bans: {ban_data['NumberOfGameBans']}"
    if ban_text == "":
        ban_text += "No bans 🎉"

    return ban_text


@client.slash_command(name="help", description="Show every command and usage.")
async def help_(ctx):
    """
    Sends a list of valid commands as an embed
    :param ctx: Context
    """
    embed = discord.Embed(title="Help Information", type="rich", color=0x0c0c28,
                          url="https://github.com/ahmetmutlugun/vapor")

    embed.add_field(name="/ping", value="Displays the bot's ping.")
    embed.add_field(name="/getid", value="Shows the linked steam account.")
    embed.add_field(name="/setid", value="Links steam account.")
    embed.add_field(name="/profile", value="Displays profile and ban information.")
    embed.add_field(name="/inventory", value="Calculate CS:GO inventory value.")
    embed.add_field(name="/item", value="Shows the price of the selected item.")
    embed.add_field(name="/csnews", value="Shows the latest CS:GO news.")
    await ctx.respond(embed=embed)


file = open("keys/discord.key", "r")
token = file.read()
file.close()
client.add_cog(Inventory(client))
client.run(token)