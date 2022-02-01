import requests
import discord
import json
from discord.ext import commands
import logging
import re

logging.log(20, "Program Started")
client = commands.Bot(description="Bringing Steam features as a Discord bot.")

headers = {'Accept': 'application/json'}
guilds = []

file = open("keys/steam.key", "r")
steam_key = file.read()


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (Discord ID: {client.user.id})")
    for guild in client.guilds:
        guilds.append(guild)


@client.slash_command(name="banstatus")
async def ban_status(ctx, steam_id):
    possible_id = get_user_id(steam_id)
    if possible_id is not None:
        data = get_player_ban(possible_id)
    else:
        data = get_player_ban(steam_id)
    if data is None:
        await ctx.respond("Could not find a player with that name or ID!")
        return
    embed = discord.Embed(title=f"Profile of {steam_id}", type='rich',
                          color=0x0c0c28, url=f"http://steamcommunity.com/profiles/{steam_id}/")
    embed.add_field(name=f"VAC Banned?", value=data['VACBanned'])
    embed.add_field(name=f"Days Since Last Ban", value=data['DaysSinceLastBan'])

    await ctx.respond(embed=embed)


@client.slash_command(name="csnews", guilds_ids=guilds)
async def cs_news(ctx):
    data = get_app_data()
    embed = discord.Embed(title=f"CSGO News", type='rich',
                          color=0x0c0c28)
    html_tags = re.compile(r'<[^>]+>')
    embed.add_field(name=f"{data['title']}", value=html_tags.sub('', data['contents']))
    await ctx.respond(embed=embed)


def get_player_ban(steam_id):
    r = requests.get(
        f' http://api.steampowered.com/ISteamUser/GetPlayerBans/v1',
        params={"key": steam_key, "steamids": f"{steam_id}"},
        headers=headers)
    data = json.loads(r.content.decode('utf-8'))
    if len(data['players']) < 1:
        return None
    return data["players"][0]


def get_app_data():
    r = requests.get(
        f' http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid=730&count=1&maxlength=30000&format=json',
        headers=headers)
    data = r.json()
    return data['appnews']['newsitems'][0]


def get_user_id(name: str):
    r = requests.get(
        f'http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={steam_key}&vanityurl={name}',
        headers=headers)
    if r.json()['response']['success'] == 1:
        return r.json()['response']['steamid']
    return None


file = open("keys/discord.key", "r")
token = file.read()
client.run(token)
