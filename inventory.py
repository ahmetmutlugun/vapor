from discord.commands import \
    slash_command, Option

from discord.ext import commands
import discord
from helpers import *

autocomplete_item_list = []
all_item_prices = {}


def set_autocomplete_items():
    all_items = get_all_item_values()

    for i in all_items:
        autocomplete_item_list.append(i)


async def get_items(ctx: discord.AutocompleteContext):
    """Returns a list of items that begin with the characters entered so far."""
    return [item for item in autocomplete_item_list if item.startswith(ctx.value)]


class Inventory(commands.Cog):
    def __init__(self, client):
        self.client = client

    @slash_command(name="inventory")
    async def get_inventory(self, ctx, steam_id=""):
        if steam_id == "":  # If the user didn't enter a steam id
            user_id_response = exec_query("SELECT steam_id FROM steam_data WHERE discord_id=(%s)",
                                          (str(ctx.author.id),))
            if user_id_response:
                steam_id = user_id_response[0][0]
            else:
                await ctx.respond(f"Please enter a Steam ID or set a steam ID with /setid")
                return
        else:
            steam_id = get_valid_steam_id(steam_id)
            if steam_id is None:
                await ctx.respond(f"Please enter a Steam ID or set a steam ID with /setid")
                return
        r = requests.get(f"https://steamcommunity.com/inventory/{steam_id}/730/2?l=english&count=5000",
                         headers=headers)
        assets = r.json()

        if assets is None:
            await ctx.respond(f"{steam_id}'s inventory is private!")
            return

        value = await calc_inventory_value(assets)
        await ctx.respond(f"Inventory value of {steam_id} is ${value}")

    @slash_command(name="item")
    async def item(self, ctx: discord.ApplicationContext, item: Option(str, "Pick an item:", autocomplete=get_items)):
        if item in autocomplete_item_list:
            r = requests.get(
                f'http://csgobackpack.net/api/GetItemPrice/?currency=USD&id={str(item).replace(" ", "%20")}&time=7&icon=1',
                headers=headers)
            try:
                await ctx.respond(f"Price of {item} is ${round(float(r.json()['median_price']), 2)}")
            except KeyError:
                await ctx.respond(f"Price of {item} is $0")
            return
        await ctx.respond("Please choose an item from the auto complete list.")


set_autocomplete_items()
