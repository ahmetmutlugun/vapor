[![Codacy Badge](https://app.codacy.com/project/badge/Grade/548b21bd9dee447db103e18ede836308)](https://www.codacy.com/gh/ahmetmutlugun/vapor/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ahmetmutlugun/vapor&amp;utm_campaign=Badge_Grade)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/ahmetmutlugun/vapor/CodeQL)  
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/ahmetmutlugun/vapor)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/ahmetmutlugun/vapor)  
![GitHub Repo stars](https://img.shields.io/github/stars/ahmetmutlugun/vapor?style=social)

# Steam Discord Bot

A discord bot made in Python to bring Steam API features into Discord. Slash commands are used to interact with the bot. 

## Commands

### Ping

```/ping```  
Displas the bot's ping to discord.

### CS:GO News 📰

```/csnews```  

Brings up the the frontpage CS:GO news, with two buttons to browse older news.  
<img src="https://media.discordapp.net/attachments/939722494523359262/955019645067345990/unknown.png" alt="profile" width="400"/>

### Profile 🗄

```/profile STEAMID```
```/profile CUSTOM_URL```  

Displays basic profile information and the oldest friends of a public steam account.  
<img src="https://media.discordapp.net/attachments/939722494523359262/955019110264225822/unknown.png" alt="profile" width="400"/>


### Inventory 🧮

```/banstatus STEAMID```
```/profile CUSTOM_URL```  

Calculates the total inventory value and displays the 5 most valuable items.  
<img src="https://media.discordapp.net/attachments/939722494523359262/955016302047682580/unknown.png" alt="inventory" width="400"/>


 ## Setup
 
### Requirements

[Docker and docker-compose](https://docs.docker.com/)
 ### Installation
 
After cloning the project, create a ./keys/ directory with ```discord.key``` and ```steam.key``` files. Discord.key will contain the discord bot token, and the steam.key file will have the steam API key [acquired here](https://steamcommunity.com/login/home/?goto=%2Fdev%2Fapikey)  

For Linux/OS X, run the following command in the project folder to create the required Docker image.  
```
docker run -p 5432:5432 -d -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=my-db -v pgdata:/var/lib/postgresql/data --name first_pg postgres
```  

Next, run the following to enter the postgres instance.  
```docker exec -ti first_pg psql -U postgres```  
In the PSQ, run the command ```\c postgres```  

And finally, run the following command to create the database.
```
CREATE TABLE steam_data(
discord_id varchar(50) NOT NULL PRIMARY KEY,
steam_id varchar(50) NOT NULL); 
```  

You can now delete the postgres instance and image. The volume "pgdata" should be ready.  
You can use ```docker-compose up``` to run the bot. 
