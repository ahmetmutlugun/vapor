import logging
import psycopg2
import requests
import json
import os
logging.basicConfig(level=logging.INFO)
headers = {'Accept': 'application/json'}
steam_key_file = open("keys/steam.key", "r")
steam_key = steam_key_file.read()
steam_key_file.close()

all_item_prices = {}


def get_valid_steam_id(steam_id):  # Check Steam ID validity or get Steam ID from custom url
    if get_player_ban(steam_id) is not None:
        return steam_id
    steam_url = get_user_id(steam_id)
    if steam_url is not None:
        return steam_url
    return None


def get_user_id(name: str):  # Get Steam ID from custom url
    r = requests.get(
        f'http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={steam_key}&vanityurl={name}',
        headers=headers)
    try:
        return r.json()['response']['steamid']
    except KeyError:
        return None


def get_player_ban(steam_id):  # Get ban infromation from Steam ID
    r = requests.get(
        f' http://api.steampowered.com/ISteamUser/GetPlayerBans/v1',
        params={"key": steam_key, "steamids": f"{steam_id}"},
        headers=headers)
    data = json.loads(r.content.decode('utf-8'))
    if len(data['players']) < 1:
        return None
    return data["players"][0]


def get_news():
    r = requests.get(
        f' http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid=730&count=1&maxlength=30000&format=json',
        headers=headers)
    data = r.json()
    return data['appnews']['newsitems'][0]


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
    item_values = get_all_item_values()
    total: float = 0
    for i in asset_list:
        try:
            total += item_values[i]['price']['24_hours']['median']
        except KeyError:
            pass
    return round(total, 2)


def get_all_item_values():
    r = requests.get(
        f'http://csgobackpack.net/api/GetItemsList/v2/',
        headers=headers)
    return r.json()['items_list']


def exec_query(query_string: str, params: tuple):
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
