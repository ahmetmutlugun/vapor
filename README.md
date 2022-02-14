[![Codacy Badge](https://app.codacy.com/project/badge/Grade/548b21bd9dee447db103e18ede836308)](https://www.codacy.com/gh/ahmetmutlugun/vapor/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ahmetmutlugun/vapor&amp;utm_campaign=Badge_Grade)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/ahmetmutlugun/vapor/CodeQL)  
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/ahmetmutlugun/vapor)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/ahmetmutlugun/vapor)  
![GitHub Repo stars](https://img.shields.io/github/stars/ahmetmutlugun/vapor?style=social)
# Steam Discord Bot
A discord bot made in Python to bring Steam API features into Discord.  

![Using Discord Slash Commands](https://media.discordapp.net/attachments/761329436582215701/937891473981050970/img.png)

## Commands
### CS:GO News
```/csnews```
Brings up the latest CS:GO news.

### Ban Status
```/banstatus STEAM_ID```
```/banstatus CUSTOM_URL```  
Find ban information of a player. Use the custom url or the steam ID

 ## Setup
### Requirements
[Docker](https://docs.docker.com/)
 ### Installation
For Linux/OSX, run the following command in the project folder to create the required Docker image.  
```docker run -p 5432:5432 -d -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=my-db -v pgdata:/var/lib/postgresql/data --name first_pg postgres```  
Next, run the following to enter the postgres instance.  
```docker exec -ti firest_pg psql -U postgres```  
In the PSQ, run the command ```\c postgres```
And finally, run this command to create the database.
```CREATE TABLE steam_data(
discord_id varchar(50) NOT NULL PRIMARY KEY,
steam_id varchar(50) NOT NULL); 
```  
You can now delete the postgres instance and image. The volume "pgdata" should be ready.  
You can use ```docker-compose-up``` to run the bot.
