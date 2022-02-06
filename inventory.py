from discord.commands import \
    slash_command
from discord.ext import commands
from helpers import *


class Inventory(commands.Cog):
    def __init__(self, client):
        self.client = client

    @slash_command(name="inventory")
    async def get_inventory(self, ctx, steam_id=""):
        steam_id = get_valid_steam_id(steam_id)
        if steam_id == "":  # If the user didn't enter a steam id
            user_id_response = exec_query("SELECT steam_id FROM steam_data WHERE discord_id=(%s)",
                                          (str(ctx.author.id),))
            if user_id_response:
                steam_id = user_id_response[0][0]
        await ctx.respond(f"Calculating inventory value for {steam_id}. This might take a few minutes.", )
        r = requests.get(f"https://steamcommunity.com/inventory/{steam_id}/730/2?l=english&count=5000",
                         headers=headers)
        assets = r.json()

        value = await calc_inventory_value(assets)
        await ctx.respond(f"Inventory value of {steam_id} is ${value}")
