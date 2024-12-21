![MCDR-Division](https://socialify.git.ci/bzyyyyyyyy/MCDR-Division/image?custom_description=%E4%B8%80%E4%B8%AA%E6%94%AF%E6%8C%81%E5%B0%86%E7%8E%A9%E5%AE%B6%E5%88%86%E7%BB%84%26%E5%90%91%E7%BB%84%2F%E7%8E%A9%E5%AE%B6%E7%95%99%E8%A8%80%E7%9A%84%E6%8F%92%E4%BB%B6&description=1&language=1&logo=https%3A%2F%2Favatars.githubusercontent.com%2Fu%2F63280128&name=1&owner=1&pattern=Floating+Cogs&theme=Light)

# MCDR-Division
---------

**中文** | [English](./README_en.md)

一个支持将玩家分组&向组/玩家留言的插件

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
