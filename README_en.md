![MCDR-Division](https://socialify.git.ci/bzyyyyyyyy/MCDR-Division/image?description=1&language=1&logo=https%3A%2F%2Favatars.githubusercontent.com%2Fu%2F63280128&name=1&owner=1&pattern=Floating+Cogs&theme=Light)

# MCDR-Division
---------

[中文](./README.md) | **English**

A plugin that supports dividing player into groups & leaving messages for groups / players

## Features

- **Player Grouping**：Supports creating multiple groups. Players can join multiple groups. Supports adding all players to one group in a time.
- **Leaving Messages**：Players can leave messages to any groups or players. Supports MC color codes. And automatically convert urls into clickable text.
- **Checking Messages**：The plugin will display all the messages leaved for the player and the groups the player is in, whenever the player logged in.
- **Multiple storage modes**：The plugin supports using JSON or redis database to store informations of groups, players, and messages.
- **Sharing Info Between Multiple Servers**：By using redis database, the plugin supports sharing informations of groups, players, and messages between multiple servers.
- **Permision Setting**：The operations of joining groups, leaving groups, deleting messages or deleting groups would be limited by MCDR permissions. 
- **Custom Color**：Supports customizing colors of groups and players in the plugin. Can be colors other than 16 MC built-in colors.
- **Latest Online Time**：The plugin will sort players according to their latest online time, and display them according to this order.
- **Time Zone Detection**：The plugin will get the time zone of the player based on its ip, and display the time based on the time zone.
- **Smooth Interaction**：Most actions can be performed by clicking texts

## Requirements

Needs `v2.1.0` + [MCDReforged](https://github.com/Fallen-Breath/MCDReforged)

Needs [OnlinePlayerAPI](https://mcdreforged.com/zh-CN/plugin/online_player_api), [Player IP Logger](https://mcdreforged.com/zh-CN/plugin/player_ip_logger)

Python package requirements: See [requirements.txt](requirements.txt)

## Command

`!!div` Display help message

`!!div search <keyword> [<page>]` Search for groups/players. It gives back all items that matches

`!!div list [<page>]` Display groups

`!!div ids [<page>]` Display players

`!!div info <group/player_id>` Display information of the group/player

`!!div make <group> [<perm>] [<color>]` Make a new group

`!!div join <group> [<player_id>]` Join the group/make the player join the group

`!!div leave <group> [<player_id>]` Leave the group/make the player leave the group

`!!div perm <group> <perm>` Change the permission level of the group

`!!div color <group> <color>` Change the color of the group

`!!div send <group/player_id> <msg>` Leave message for the group/player

`!!div edit <group/player_id> <lineNo.> <msg>` Change the message at `<lineNo.>` of the group/player

`!!div del <group/player_id> <lineNo.>` Delete the message at `<lineNo.>` of the group/player

`!!div del <group/player_id>` Delete the group

`!!div confirm` Use after deleting to confirm the execution

`!!div place <group> <pos>` Change the position of the group

`!!div check [time/group]` Check the messages people have left for you, can be in time order or group order

`!!div <keyword> [<page>]` Same to `!!div search`
