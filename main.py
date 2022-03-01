import asyncio
import json
import logging
import re
from abc import ABC

import discord
from discord.ext import commands
from discord.ext import tasks
from discord.ext.commands import has_permissions

from global_commands import Global
from helpers import get_news, get_valid_steam_id, exec_query
from inventory import Inventory

# TODO
# Respond with the linked profile to /getid and /setid
# Add user profile command to display profile embeds

logging.basicConfig(level=logging.INFO)
logging.info("Running Script...")
NEWS_CHANNEL = 891028959041585162
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
    logging.info(f"Logged in as {client.user} (Discord ID: {client.user.id})")
    for guild in client.guilds:
        guilds.append(guild)


@client.slash_command(name="csnews", guilds_ids=guilds, description="Show the latest CS:GO news.")
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
    html_tags = re.compile(r'<[^>]+>')
    embed = discord.Embed(title=f"CSGO News", type='rich', color=0x0c0c28, url=front_page['url'].replace(" ", ""))
    embed.add_field(name=front_page['title'], value=html_tags.sub('', articles[0]['contents']))

    return embed


file = open("keys/discord.key", "r")
token = file.read()
file.close()
client.add_cog(Inventory(client))
client.add_cog(Global(client))
client.run(token)
