import logging
import time

from discord.commands import \
    slash_command, Option

from discord.ext import commands
import discord
import requests

from cogs import firebase
from cogs.helpers import get_all_item_values, calc_inventory_value, get_valid_steam_id, headers, \
    get_player_profile

autocomplete_item_list = []


def set_autocomplete_items(autocomplete_items=None):
    """
    Creates a list of CS:GO items
    :return: List of CS:GO items
    """

    all_items = get_all_item_values()
    all_items = requests.get("https://api.steamapis.com/image/items/730")
    autocomplete_items += all_items.json().keys()


async def get_items(ctx: discord.AutocompleteContext):
    """
    Autocompletes items from the autocomplete_item_list
    :param ctx: Context
    :return: list of matching items
    """
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
    """
    Discord Cog for item and inventory commands
    """

    def __init__(self, client):
        """
        Cog for inventory and item price commands
        :param client: discord client
        """
        self.client = client

    @slash_command(name="inventory", description="Check total inventory price.")
    async def get_inventory(self, ctx, steam_id=""):
        """
        Send total inventory value and top items of a user to discord.
        Checks if the steam id is valid, or uses the saved steam id
        :param ctx: Context
        :param steam_id: steam id of a steam user
        :return: None if an error occurs
        """
        if steam_id == "":  # If the user didn't enter a steam id
            steam_id = firebase.get_steam_id(ctx.author.id)
            if steam_id is None:
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
        data = get_player_profile(steam_id)

        if assets is None:
            await ctx.respond(f"{steam_id}'s inventory is private!")
            return

        results = await calc_inventory_value(assets)
        embed = discord.Embed(title=f"CS:GO Inventory Value of {data['personaname']}", type='rich',
                              color=0x0c0c28,
                              url=data['profileurl'] + "inventory/")
        embed.add_field(name="Total Value", value=f"${results[0]}", inline=False)
        embed.add_field(name="Top Items:", value=results[1])
        embed.set_author(name=data['personaname'], icon_url=data['avatar'], url=data['profileurl'])
        await ctx.respond(embed=embed)

    @slash_command(name="item", description="Shows individual item prices.")
    async def item(self, ctx: discord.ApplicationContext, item: Option(str, "Pick an item:", autocomplete=get_items)):
        """
        Get price and stock data of a CS:GO item
        :param ctx: Context
        :param item: CS:GO item
        :return: None if an error occurs
        """
        single_quote = "\'"
        item_url = f'https://csgobackpack.net/api/GetItemPrice/?currency=USD&id={str(item).replace(" ", "%20").replace("&#39", single_quote)}&time=7&icon=1'
        if item in autocomplete_item_list:
            r = requests.get(
                item_url,
                headers=headers)

            try:
                # Create an embed with the items stats

                embed = discord.Embed(title=f"{item}", type='rich',
                                      color=0x0c0c28,
                                      url=item_url)
                embed.add_field(name="Average Price:", value=f"${round(float(r.json()['average_price']), 2)}")
                embed.add_field(name="Median Price:", value=f"${round(float(r.json()['median_price']), 2)}")
                embed.add_field(name="Amount on sale:", value=r.json()['amount_sold'])
                embed.set_thumbnail(url=r.json()['icon'])
                await ctx.respond(embed=embed)
            except KeyError:
                await ctx.respond(f"Could not find a price for {item}!")
            return
        await ctx.respond("Please choose an item from the auto complete list.")


set_autocomplete_items(autocomplete_item_list)
