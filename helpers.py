import logging
import psycopg2
import requests
import json
import os

headers = {'Accept': 'application/json'}
steam_key_file = open("keys/steam.key", "r")
steam_key = steam_key_file.read().replace("\n", "")
steam_key_file.close()

all_item_prices = {}  # Cache item prices


def set_all_item_prices():
    """
    Assigns items names to item prices in the dictionary all_item_prices
    """
    items = get_all_item_values()  # has &#39

    for i in items:
        try:
            all_item_prices.update({i: items[i]['price']['24_hours']['median']})
        except KeyError:
            try:
                all_item_prices.update({i: items[i]['price']['7_days']['median']})
            except KeyError:
                try:
                    all_item_prices.update({i: items[i]['price']['30_days']['median']})
                except KeyError:
                    try:
                        all_item_prices.update({i: items[i]['price']['all_time']['median']})
                    except KeyError:
                        all_item_prices.update({i: 0})


def get_player_friends(steam_id):
    """
    Get a users friend list, and return as a dictionary with steam ids and friend date
    Sorted by add date
    :param steam_id: steam ID of a steam user
    :return: list of friends. return none if steam profile is private
    """
    r = requests.get(
        'http://api.steampowered.com/ISteamUser/GetFriendList/v0001/',
        headers=headers, params={'steamid': [steam_id], "key": steam_key, 'relationship': "friend"})
    friends = {}
    try:
        for i in r.json()['friendslist']['friends']:
            friends.update({i['steamid']: i['friend_since']})
        friends = dict(sorted(friends.items(), key=lambda x: x[1]))
    except KeyError:
        return None
    return friends


def get_player_profile(steam_id):
    """
    Gets profile information of a steam user
    :param steam_id: steam ID of a steam user
    :return: Player Profile. None if an invalid steam ID is given
    """
    r = requests.get(
        'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/',
        headers=headers, params={'steamids': [steam_id], "key": steam_key})
    try:
        return r.json()['response']['players'][0]
    except KeyError:
        return None


def get_valid_steam_id(steam_id):
    """
    Checks if a steam ID is valid and returns a valid steamid.
    If a custom url is given, steam_id is returned
    :param steam_id: steam ID of a steam user
    :return: steam ID of a steam user
    """
    if get_player_ban(steam_id) is not None:
        return steam_id
    steam_url = get_user_id(steam_id)
    if steam_url is not None:
        return steam_url
    return None


def get_user_id(name: str):
    """
    Gets user's steam id from vanity url
    :param name: steam vanity url (custom url)
    :return: steam id
    """
    r = requests.get(
        f'http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={steam_key}&vanityurl={name}',
        headers=headers)
    try:
        return r.json()['response']['steamid']
    except KeyError:
        return None


def get_player_ban(steam_id):
    """
    Get ban information from steam id
    :param steam_id: steam id from a steam profile
    :return: ban data in json format
    """
    r = requests.get(
        ' http://api.steampowered.com/ISteamUser/GetPlayerBans/v1',
        params={"key": steam_key, "steamids": f"{steam_id}"},
        headers=headers)
    data = r.json()
    if len(data['players']) < 1:
        return None
    return data["players"][0]


def get_news(count: int = 1, appid: int = 730):
    """
    Get a number of app news
    :param count: Number of news
    :param appid: Steam ID app id
    :return: returns news from the given appid
    """
    r = requests.get(
        f' http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={appid}&count={count}&maxlength=30000&format=json',
        headers=headers)
    data = r.json()
    return data['appnews']['newsitems']


# Please don't look at this mess...
async def calc_inventory_value(assets):
    """
    Calculates the total CS:GO inventory value of a user, and returns the top 5 most valuable items in the inventory
    :param assets: Assets of a steam inventory as returned by the steam api
    :return: total value, top 5 items in a tuple
    """
    single_quote = "\'"
    # Find number of item
    id_dictionary = {}
    for i in assets['assets']:
        if i['classid'] in id_dictionary:
            id_dictionary.update({i['classid']: id_dictionary[i['classid']] + 1})
        else:
            id_dictionary.update({i['classid']: 1})

    asset_list = []
    asset_dict = {}
    total: float = 0.0
    for i in assets['descriptions']:
        for _ in range(0, id_dictionary[i['classid']]):
            asset_list.append(i['market_hash_name'].replace(single_quote, "&#39"))
            try:
                total += all_item_prices[i['market_hash_name'].replace(single_quote, "&#39")]
                asset_dict.update({all_item_prices[i['market_hash_name'].replace(single_quote, "&#39")]: i[
                    'market_hash_name'].replace(single_quote, "&#39")})
            except KeyError:
                pass
    item_values = list(sorted(asset_dict))[::-1]
    top_items = ""
    length = len(item_values)
    if length > 5:
        length = 5
    for item_value in item_values[0:length]:
        top_items += f"{str(asset_dict.get(item_value)).replace('&#39', single_quote, )}: ${item_value}\n"
    return round(total, 2), top_items


def get_all_item_values():
    """
    Gets the list of items and prices from CS:GO backpack.
    :return: List of items and their prices
    """
    r = requests.get(
        'http://csgobackpack.net/api/GetItemsList/v2/',
        headers=headers)
    return r.json()['items_list']


def exec_query(query_string: str, params: tuple) -> object:
    """
    Queries Postgres SQL DB.
    :param query_string: SQL query
    :param params: Queried items
    :return: results from the database
    """
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


def query_steam_id(author_id):
    """
    Gets steam id from author id
    :param author_id: discord id
    :return: steam id
    """
    user_id_response = exec_query("SELECT steam_id FROM steam_data WHERE discord_id=(%s)", (str(author_id),))
    if user_id_response:
        return user_id_response[0][0]
    return


async def cs_status():
    """
    Get CS:GO Server Status
    :return: API JSON
    """
    r = requests.get(url=f"https://api.steampowered.com/ICSGOServers_730/GetGameServersStatus/v1/?key={steam_key}",
                     headers=headers)
    if r.status_code == 200:
        return r.json()
    return None


set_all_item_prices()