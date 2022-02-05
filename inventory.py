import requests

headers = {'Accept': 'application/json'}


def get_steam_item_values():
    r = requests.get(
        f'http://csgobackpack.net/api/GetItemsList/v2/',
        headers=headers, params={'no_details': 1})
    data = r.json()
    return data['items_list']


def item_value(item: str):
    r = requests.get(
        f'http://csgobackpack.net/api/GetItemPrice/?currency=USD&id={item}&time=7&icon=1',
        headers=headers, params={'id': item.replace(' ', '%20')})
    print(r.json())
    try:
        price = float(r.json()['median_price'])
    except KeyError:
        return 0
    return price


def get_inventory():
    r = requests.get(f"https://steamcommunity.com/inventory/76561198351198684/730/2?l=english&count=5000",
                     headers=headers)
    return r.json()


id_dictionary = {}
item_count = 0
for i in get_inventory()['assets']:
    if i['classid'] in id_dictionary:
        id_dictionary.update({i['classid']: id_dictionary[i['classid']] + 1})
        item_count+=1
    else:
        id_dictionary.update({i['classid']: 1})
        item_count+=1
print(item_count)
print(id_dictionary)

assets = get_inventory()['descriptions']

asset_list = []
for i in assets:
    for _ in range(0, id_dictionary[i['classid']]):
        asset_list.append(i['market_hash_name'])
total = 0
for i in asset_list:
    total += item_value(i)
    print(item_value(i))
    print(i)


asset_list = get_inventory()

print(total)