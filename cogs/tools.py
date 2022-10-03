import discord
from discord import slash_command
from discord.ext import commands


class Tools(commands.Cog):
    """
    Discord Cog for item and inventory commands
    """

    def __init__(self, client):
        """
        Cog for inventory and item price commands
        :param client: discord client
        """
        self.client = client

    @slash_command(name="help", description="Show every command and usage.")
    async def help_(self, ctx):
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
