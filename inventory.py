import json

import requests
from discord import Option
from discord.commands import \
    slash_command
from discord.ext import commands
import psycopg2
import os

headers = {'Accept': 'application/json'}
file2 = open("keys/steam.key", "r")
steam_key = file2.read()
file2.close()


def item_value(item: str):
    r = requests.get(
        f'http://csgobackpack.net/api/GetItemPrice/?currency=USD&id={item}&time=7&icon=1',
        headers=headers, params={'id': item.replace(' ', '%20')})

    try:
        price = float(r.json()['median_price'])
    except KeyError:
        return 0
    return price


def get_valid_steam_id(steam_id):
    if get_player_ban(steam_id) is not None:
        return steam_id
    steam_url = get_user_id(steam_id)
    if steam_url is not None:
        return steam_url
    return None


def get_user_id(name: str):
    r = requests.get(
        f'http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={steam_key}&vanityurl={name}',
        headers=headers)
    if r.json()['response']['success'] == 1:
        return r.json()['response']['steamid']
    return None


def get_player_ban(steam_id):
    r = requests.get(
        f' http://api.steampowered.com/ISteamUser/GetPlayerBans/v1',
        params={"key": steam_key, "steamids": f"{steam_id}"},
        headers=headers)
    data = json.loads(r.content.decode('utf-8'))
    if len(data['players']) < 1:
        return None
    return data["players"][0]


async def calc_inventory_value(assets):
    id_dictionary = {}
    for i in assets['assets']:
        if i['classid'] in id_dictionary:
            id_dictionary.update({i['classid']: id_dictionary[i['classid']] + 1})
        else:
            id_dictionary.update({i['classid']: 1})
    asset_list = []
    for i in assets['descriptions']:
        for _ in range(0, id_dictionary[i['classid']]):
            asset_list.append(i['market_hash_name'])

    total: float = 0
    for i in asset_list:
        total += item_value(i)
    return round(total, 2)


class Inventory(commands.Cog):
    def __init__(self, client):
        self.client = client

    @slash_command(name="inventory")
    async def get_inventory(self, ctx, steam_id = ""):
        steam_id = get_valid_steam_id(steam_id)
        if steam_id == "":  # If the user didn't enter a steam id
            user_id_response = self.exec_query("SELECT steam_id FROM steam_data WHERE discord_id=(%s)",
                                               (str(ctx.author.id),))
            if user_id_response:
                steam_id = user_id_response[0][0]
        await ctx.respond(f"Calculating inventory value for {steam_id}. This might take a few minutes.", )
        r = requests.get(f"https://steamcommunity.com/inventory/{steam_id}/730/2?l=english&count=5000",
                         headers=headers)
        assets = r.json()

        value = await calc_inventory_value(assets)
        await ctx.respond(f"Inventory value of {steam_id} is ${value}")

    def exec_query(self, query_string: str, params: tuple):
        res = []
        # Establish a session with the postgres database
        with psycopg2.connect(
                host=os.environ["HOST"],
                database=os.environ["POSTGRES_DB"],
                user=os.environ["POSTGRES_USER"],
                password=os.environ["POSTGRES_PASSWORD"]
        ) as conn:
            # Create a cursor
            with conn.cursor() as cur:
                # Execute query with parameters
                cur.execute(query_string, params)
                try:
                    res = cur.fetchall()
                except psycopg2.ProgrammingError:
                    res = []
        # Return all the results
        return res

