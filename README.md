![MCDR-Division](https://socialify.git.ci/bzyyyyyyyy/MCDR-Division/image?custom_description=%E4%B8%80%E4%B8%AA%E6%94%AF%E6%8C%81%E5%B0%86%E7%8E%A9%E5%AE%B6%E5%88%86%E7%BB%84%26%E5%90%91%E7%BB%84%2F%E7%8E%A9%E5%AE%B6%E7%95%99%E8%A8%80%E7%9A%84%E6%8F%92%E4%BB%B6&description=1&language=1&logo=https%3A%2F%2Favatars.githubusercontent.com%2Fu%2F63280128&name=1&owner=1&pattern=Floating+Cogs&theme=Light)

# MCDR-Division
---------

**中文** | [English](./README_en.md)

一个支持将玩家分组&向组/玩家留言的插件

## 功能

- **玩家分组**：支持创建多个不同的组，玩家可以同时进入多个组，支持一键将所有玩家加入组
- **发送留言**：玩家可以自由地向组或者玩家留言，支持MC的颜色代码，以及自动将网址转换为可被点击的文字
- **查看留言**：每次玩家上线时，将会显示留给该玩家和该玩家进入的组的留言，可选以日期顺序或以组顺序排列
- **多种存储方式**：插件支持使用JSON或redis数据库存储组，玩家以及留言信息
- **多服共享信息**：使用redis数据库存储信息支持多个服共享组，玩家以及留言信息
- **权限设置**：根据MCDR权限限制玩家加入组，退出组，删除留言，删除组的操作
- **自定义颜色**：支持自定义插件中的组或玩家的颜色，不限于MC自带的16种颜色
- **最近在线时间显示**：插件将根据最近在线时间对玩家进行排序，并根据此顺序显示玩家列表
- **时区检测**：插件将根据玩家的ip获取该玩家的时区，并根据时区显示所有插件记录的时间
- **流畅交互**：大部分操作都能通过点击文字执行

## 依赖

需要 `v2.1.0` 以上的 [MCDReforged](https://github.com/Fallen-Breath/MCDReforged)

需要 [OnlinePlayerAPI](https://mcdreforged.com/zh-CN/plugin/online_player_api)，[Player IP Logger](https://mcdreforged.com/zh-CN/plugin/player_ip_logger)

Python 包要求：见 [requirements.txt](requirements.txt)

## 命令格式说明

`!!div` 显示帮助信息

`!!div search <keyword> [<page>]` 搜索组/玩家，返回所有匹配项

`!!div list [<page>]` 显示所有组

`!!div ids [<page>]` 显示所有玩家

`!!div info <group/player_id>` 显示组/玩家的信息

`!!div make <group> [<perm>] [<color>]` 创建一个新组

`!!div join <group> [<player_id>]` 加入组/让玩家加入组

`!!div leave <group> [<player_id>]` 离开组/让玩家离开组

`!!div perm <group> <perm>` 更改组的使用权限

`!!div color <group> <color>` 更改组的颜色

`!!div send <group/player_id> <msg>` 向组/玩家留言

`!!div edit <group/player_id> <lineNo.> <msg>` 修改组/玩家的第`<lineNo.>`行留言

`!!div del <group/player_id> <lineNo.>` 删除组/玩家的第`<lineNo.>`行留言

`!!div del <group/player_id>` 删除组

`!!div confirm` 再次确认是否删除组/留言

`!!div place <group> <pos>` 更改组的显示位置

`!!div check [time/group]` 查看留给自己的言，可选以日期顺序或以组顺序排列

`!!div <keyword> [<page>]` 同 `!!div search`
