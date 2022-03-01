from discord.ext import commands
from discord.commands import \
    slash_command
from helpers import get_player_ban, get_player_profile, get_player_friends, query_steam_id, get_user_id, \
    get_valid_steam_id, exec_query
import discord


def format_ban_text(ban_data):
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


def generate_profile_embed(steam_id, author):
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


class Global(commands.Cog):
    def __init__(self, client):
        """
        Cog for general, global commands

        :param client: discord client
        """
        self.client = client

    @slash_command(name='ping', description="Displays latency.")
    async def ping(self, ctx):
        await ctx.respond(f"My ping is: {round(self.client.latency * 1000)}ms")

    @slash_command(name="profile", description="Show the profile of a steam user.")
    async def profile(self, ctx, steam_id=""):
        if (i := generate_profile_embed(steam_id, ctx.author.id)) is not None:
            await ctx.respond(embed=i)
        else:
            await ctx.respond("Please provide a Steam ID or use /setid.")

    @slash_command(name="getid", description="Get saved steam account")
    async def get_id(self, ctx):
        # steam_id = query_steam_id(ctx.author.id)
        # if steam_id is None:
        #     await ctx.respond("Please use /setid to set your Steam ID!")
        #     return
        # await ctx.respond(f"Your steam ID is: {steam_id}")

        if (i := generate_profile_embed(query_steam_id(ctx.author.id), ctx.author.id)) is not None:
            await ctx.respond(embed=i)
        else:
            await ctx.respond("Please use /setid to set your Steam ID!")

    @slash_command(name="help", description="Show every command and usage.")
    async def help_(self, ctx):
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

    @slash_command(name="setid", description="Link a steam account to your account")
    async def set_id(self, ctx, steam_id: str):
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
