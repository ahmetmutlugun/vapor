import logging
import time

import psycopg2
import requests
import json
import os

headers = {'Accept': 'application/json'}
steam_key_file = open(os.getcwd() + "/keys/steam.key", "r")
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
    data = api_request('http://api.steampowered.com/ISteamUser/GetFriendList/v0001/',
                       parameters={'steamid': [steam_id], "key": steam_key, 'relationship': "friend"})
    friends = {}
    try:
        for i in data['friendslist']['friends']:
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
    data = api_request('http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/',
                       parameters={'steamids': [steam_id], "key": steam_key})
    try:
        return data['response']['players'][0]
    except (KeyError, IndexError):
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
    data = api_request(
        f'http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={steam_key}&vanityurl={name}')
    try:
        return data['response']['steamid']
    except KeyError:
        return None


def get_player_ban(steam_id):
    """
    Get ban information from steam id
    :param steam_id: steam id from a steam profile
    :return: ban data in json format
    """
    data = api_request('http://api.steampowered.com/ISteamUser/GetPlayerBans/v1',
                       parameters={"key": steam_key, "steamids": f"{steam_id}"})
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
    return api_request(
        f' http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={appid}&count={count}&maxlength=30000&format=json')[
        'appnews']['newsitems']


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
    return api_request('http://csgobackpack.net/api/GetItemsList/v2/')['items_list']


async def cs_status():
    """
    Get CS:GO Server Status
    :return: API JSON
    """
    return api_request(f"https://api.steampowered.com/ICSGOServers_730/GetGameServersStatus/v1/?key={steam_key}")


def api_request(req_url: str, parameters=None):
    r = requests.get(url=req_url,
                     headers={'Accept': 'application/json'}, params=parameters)
    if r.status_code == 200:
        return r.json()
    return None
