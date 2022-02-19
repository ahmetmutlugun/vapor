from discord.commands import \
    slash_command, Option

from discord.ext import commands
import discord
import requests
from helpers import get_all_item_values, exec_query, calc_inventory_value, get_valid_steam_id, headers

autocomplete_item_list = []
all_item_prices = {}


def set_autocomplete_items():
    all_items = get_all_item_values()

    for i in all_items:
        autocomplete_item_list.append(i)


async def get_items(ctx: discord.AutocompleteContext):
    matching_items = []
    for item in autocomplete_item_list:
        item_list = ctx.value.lower().split(" ")
        failed = False
        for _ in item_list:
            if _ not in item.lower():
                failed = True
        if not failed:
            matching_items.append(item)
    return matching_items


class Inventory(commands.Cog):
    def __init__(self, client):
        """
        Cog for inventory and item price commands

        :param client: discord client
        """
        self.client = client

    @slash_command(name="inventory", description="Check total inventory price.")
    async def get_inventory(self, ctx, steam_id=""):
        if steam_id == "":  # If the user didn't enter a steam id
            user_id_response = exec_query("SELECT steam_id FROM steam_data WHERE discord_id=(%s)",
                                          (str(ctx.author.id),))
            if user_id_response:
                steam_id = user_id_response[0][0]
            else:
                await ctx.respond("Please enter a Steam ID or set a steam ID with /setid")
                return
        else:
            steam_id = get_valid_steam_id(steam_id)
            if steam_id is None:
                await ctx.respond("Please enter a Steam ID or set a steam ID with /setid")
                return
        r = requests.get(f"https://steamcommunity.com/inventory/{steam_id}/730/2?l=english&count=5000",
                         headers=headers)
        assets = r.json()

        if assets is None:
            await ctx.respond(f"{steam_id}'s inventory is private!")
            return

        value = await calc_inventory_value(assets)
        await ctx.respond(f"Inventory value of {steam_id} is ${value}")

    @slash_command(name="item", description="Shows individual item prices.")
    async def item(self, ctx: discord.ApplicationContext, item: Option(str, "Pick an item:", autocomplete=get_items)):
        if item in autocomplete_item_list:
            r = requests.get(
                f'http://csgobackpack.net/api/GetItemPrice/?currency=USD&id={str(item).replace(" ", "%20")}&time=7&icon=1',
                headers=headers)
            try:
                # Create an embed with the items stats
                embed = discord.Embed(title=f"{item}", type='rich',
                                      color=0x0c0c28,
                                      url=f"https://steamcommunity.com/market/listings/730/{str(item).replace(' ', '%20')}")
                embed.add_field(name="Average Price:", value=f"${round(float(r.json()['average_price']), 2)}")
                embed.add_field(name="Median Price:", value=f"${round(float(r.json()['median_price']), 2)}")
                embed.add_field(name="Amount on sale:", value=r.json()['amount_sold'])
                embed.set_thumbnail(url=r.json()['icon'])
                await ctx.respond(embed=embed)
            except KeyError:
                await ctx.respond(f"Could not find a price for {item}!")
            return
        await ctx.respond("Please choose an item from the auto complete list.")


set_autocomplete_items()
