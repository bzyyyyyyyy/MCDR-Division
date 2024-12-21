import re
from typing import Any, Optional, List
import requests
import pytz
from datetime import datetime, timedelta
import os
from math import ceil
import re

from mcdreforged.api.all import *

from division.confirm import Confirm
from division.constants import CONFIG_FILE, PREFIX, GROUPS_STORAGE_FILE, PLAYERS_STORAGE_FILE, GROUP_OF_ALL
from division.storage.storage import GroupStorage, Group, PlayerStorage, Player, Item, Storage, OtherStorage, \
    build_player, build_other_storage, Msg
from division.storage.direct import DirectGroupStorage, DirectPlayerStorage
from division.storage.redis_s import RedisGroupStorage, RedisPlayerStorage, init_redis



class Config(Serializable):
    item_per_page: int = 10
    default_perm: int = 1
    default_color: str = 'white'
    default_sender: str = 'server'
    default_check_mode: str = 'time'
    perm_to_modify_all: int = 1
    msg_for_new_player: str = ''
    redis_ip: str = ''
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ''


config: Config
group_storage: (Storage, GroupStorage)
player_storage: (Storage, PlayerStorage)
other_storage: OtherStorage
server_inst: PluginServerInterface
HelpMessage: RTextBase
online_player_api: Optional[Any]
player_ip_logger: Optional[Any]
confirm: Confirm = Confirm()


def handle_get_storage():
    global group_storage, player_storage, other_storage
    if config.redis_ip:
        init_redis(host=config.redis_ip, port=config.redis_port, db=config.redis_db, password=None if config.redis_password == '' else config.redis_password)

        player_storage = RedisPlayerStorage()
        group_storage = RedisGroupStorage()

        if player_storage.first_load:
            player_storage.add_item(config.default_sender, build_player('127.0.0.1'))
            online_players = online_player_api.get_player_list()
            for player_id in online_players:
                if player_ip_logger.is_player(player_id):
                    ips = player_ip_logger.get_player_ips(player_id)
                    if len(ips) == 0:
                        ips[0] = ''
                    player_storage.add_item(player_id, build_player(ips[0]))

        other_storage = build_other_storage('redis')

        if group_storage.first_load:
            group_storage.add_item('broadcast', Group(perm=4, color='gold'))
            handle_join_all(server_inst.get_plugin_command_source(), 'broadcast')

    else:
        player_storage = DirectPlayerStorage()
        group_storage = DirectGroupStorage()

        if player_storage.load(os.path.join(server_inst.get_data_folder(), PLAYERS_STORAGE_FILE)):
            player_storage.add_item(config.default_sender, build_player('127.0.0.1'))
            online_players = online_player_api.get_player_list()
            for player_id in online_players:
                if online_player_api.is_player(player_id):
                    ips = online_player_api.get_player_ips(player_id)
                    if len(ips) == 0:
                        ips[0] = ''
                    player_storage.add_item(player_id, build_player(ips[0]))

        if group_storage.load(os.path.join(server_inst.get_data_folder(), GROUPS_STORAGE_FILE)):
            group_storage.add_item('broadcast', Group(perm=4, color='gold'))
            handle_join_all(server_inst.get_plugin_command_source(), 'broadcast')

        other_storage = build_other_storage('direct')


def tr(translation_key: str, *args) -> RTextMCDRTranslation:
    return ServerInterface.get_instance().rtr(f'division.{translation_key}', *args)


def print_message(source: CommandSource, msg, tell=True, prefix: Any = '', tell_player: str = None):
    msg = RTextList(prefix, msg)
    if tell_player is not None:
        server_inst.tell(tell_player, msg)
    if source.is_player and not tell:
        source.get_server().say(msg)
    else:
        source.reply(msg)


def print_unknown(source: CommandSource, name, item: str = 'group'):
    print_message(source, tr(f'command.unknown_{item}', RText(name, color=RColor.from_mc_value(config.default_color))))


def command_run(message: Any, text: Any, command: str) -> RTextBase:
    fancy_text = message.copy() if isinstance(message, RTextBase) else RText(message)
    return fancy_text.set_hover_text(text).set_click_event(RAction.run_command, command)


def print_help_message(source: CommandSource):
    if source.is_player:
        source.reply('')
    with source.preferred_language_context():
        for line in HelpMessage.to_plain_text().splitlines():
            prefix = re.search(r'(?<=§7){}[\w ]*(?=§)'.format(PREFIX), line)
            if prefix is not None:
                print_message(source, RText(line).set_click_event(RAction.suggest_command, prefix.group()))
            else:
                print_message(source, line)


def req_perm(source: CommandSource, perm):
    if source.is_player and not source.has_permission(perm):
        source.reply(tr('command.permission_denied'))
        return True
    return False


def req_is_player(source: CommandSource, player_id):
    if isinstance(source, PlayerCommandSource) and source.player != player_id:
        source.reply(tr('command.not_the_player', player_RText(player_id)))
        return True
    return False


def ip_to_tz(ip: str) -> str | None:
    data = requests.get(f'http://ip-api.com/json/{ip}?fields=status,message,timezone').json()
    if data['status'] == 'success':
        return data['timezone']
    else:
        return None


def get_tz(source: CommandSource):
    try:
        return pytz.timezone(ip_to_tz(player_storage.get(source.player).ip))
    except Exception as e:
        return None


def get_dt_tz(source: CommandSource, time_t: float, tz):
    dt = datetime.fromtimestamp(time_t, tz)
    return dt, tz


def disp_time(source: CommandSource, time_t: float, tz=None) -> str:
    dt, tz = get_dt_tz(source, time_t, tz)
    now = datetime.now(tz)
    zeroToday = now - timedelta(hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
    zeroYTD = zeroToday - timedelta(days=1)
    sixDaysBefore = zeroToday - timedelta(days=6)
    startOfYear = zeroToday.replace(month=1, day=1)
    if dt > zeroToday:
        return dt.strftime('%H:%M')
    elif dt > zeroYTD:
        return tr('time.yesterday') + dt.strftime(' %H:%M')
    elif dt > sixDaysBefore:
        return dt.strftime('%a %H:%M')
    elif dt > startOfYear:
        return dt.strftime('%m.%d')
    else:
        return dt.strftime('%Y.%m.%d')


def format_time(source: CommandSource, time_t: float, tz=None):
    dt, tz = get_dt_tz(source, time_t, tz)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def group_RText(name: str, context: str = None) -> RText:
    text = name
    try:
        text = context.format(name)
    except Exception as e:
        pass
    if group_storage.contains(name):
        return RText(text, color=group_storage.get(name).get_color()). \
            h(tr('info.group')). \
            c(RAction.run_command, f'{PREFIX} info {name}')
    return RText(text, color=RColor.from_mc_value(config.default_color))


def show_groups(groups):
    msg: Any = ''
    for name in groups:
        msg += group_RText(name, '[{}] ')
    return msg


def player_RText(name: str, context: str = None) -> RText:
    text = name
    try:
        text = context.format(name)
    except Exception as e:
        pass
    if name == GROUP_OF_ALL:
        return RText(text, color=RColor.from_mc_value('gold')). \
            h(tr('info.list_players')). \
            c(RAction.run_command, f'{PREFIX} ids')
    if player_storage.contains(name):
        return RText(text, color=player_storage.get(name).get_color()). \
            h(tr('info.player')). \
            c(RAction.run_command, f'{PREFIX} info {name}')
    return RText(text, color=RColor.from_mc_value(config.default_color))


def show_members(ids):
    msg: Any = ''
    for name in ids:
        msg += player_RText(name, '<{}> ')
    return msg


def handle_info_update_latest_online_time(name: str):
    if name == config.default_sender or online_player_api.check_online(name):
        player_storage.update_latest_online_time(name)


def handle_default_sender_change(new: str, old: str):
    def change_item(name, item: Item):
        def change_sender(msg):
            if msg.sender == old:
                msg.set_sender(new)

        item.for_each_msg(change_sender)

    def change_id_in_group(name, group: Item):
        if isinstance(group, Group):
            if group.leave(old):
                group.join(new)

    if player_storage.contains(old):
        player_storage.add_item(new, player_storage.pop_item(old))
    else:
        player_storage.add_item(new, build_player('127.0.0.1'))
    group_storage.for_each(change_id_in_group)
    group_storage.for_each(change_item)
    player_storage.for_each(change_item)


def handle_config_change(new: Config, old: Config):
    if new.default_sender != old.default_sender:
        handle_default_sender_change(new.default_sender, old.default_sender)


def log(msg):
    print_message(server_inst.get_plugin_command_source(), msg)


def handle_join_all(source: CommandSource, name: str):
    try:
        if group_storage.join(name, GROUP_OF_ALL):
            try:
                other_storage.add_group_for_all(name)
            except Exception as e:
                pass
            player_storage.for_each(lambda n, value: value.join(name))
            print_message(source, tr('join_group.success_all', group_RText(name)))
        else:
            print_message(source, tr('join_group.exist_all', group_RText(name)))
    except Exception as e:
        print_message(source, tr('join_group.fail_all', group_RText(name), e))
        server_inst.logger.exception('Failed to make all players join group {}'.format(name))


def handle_leave_all(source: CommandSource, name: str):
    group = group_storage.get(name)
    try:
        if group_storage.leave(name, GROUP_OF_ALL):
            other_storage.remove_group_for_all(name)

            def func(n, value: Player):
                if not group.in_list(n):
                    value.leave(name)

            player_storage.for_each(func)
            print_message(source, tr('leave_group.success_all', group_RText(name)))
        else:
            print_message(source, tr('leave_group.not_exist_all', group_RText(name)))
    except Exception as e:
        print_message(source, tr('leave_group.fail_all', group_RText(name), e))
        server_inst.logger.exception('Failed to make all players leave group {}'.format(name))


def interpreter(text: str) -> str:
    return text.replace('$', '§').replace('§§', '$')


def reverse_interpreter(text: str) -> str:
    return text.replace('$', '$$').replace('§', '$')


def url_tr(text: str) -> RTextList:
    pattern = r'(http[^\s]*)'
    result = RTextList()
    last_end = 0
    for match in re.finditer(pattern, text):
        start, end = match.span()
        if start > last_end:
            result.append(text[last_end:start])
        result.append(RText(match.group(1)).h(tr('url')).c(RAction.open_url, match.group(1)))
        last_end = end
    if last_end < len(text):
        result.append(text[last_end:])

    return result


@new_thread('info')
def info(source: CommandSource, name: str):
    item = group_storage.get(name)
    if item is None:
        item = player_storage.get(name)
    if item is not None:
        tz = get_tz(source)
        item_type = 'player' if isinstance(item, Player) else 'group'
        print_message(
            source,
            RTextList(tr(f'info.name.{item_type}') + RText(name, color=item.get_color())).
            h(tr(f'info.{item_type}')).
            c(RAction.run_command, f'{PREFIX} info {name}')
        )
        if isinstance(item, Player):
            handle_info_update_latest_online_time(name)
            item = player_storage.get(name)
            print_message(
                source,
                RTextList(tr('info.latest_online_time') +
                          RText(disp_time(source, item.latest_online_time, tz), color=RColor.gray)).
                h(format_time(source, item.latest_online_time, tz)) +
                '\n' +
                tr('info.show_groups') +
                '\n' +
                show_groups(group_storage.ordered_items(item.list))
            )
        elif isinstance(item, Group):
            members = player_storage.ordered_items(item.list)
            if GROUP_OF_ALL in item.list:
                members.insert(0, GROUP_OF_ALL)
            print_message(
                source,
                RText(tr('info.perm.header', item.perm)).
                h(tr('info.perm.hover')).
                c(RAction.suggest_command, f'{PREFIX} perm {name} ') +
                '\n' +
                tr('info.show_players') +
                '\n' +
                show_members(members)
            )
            if isinstance(source, PlayerCommandSource):
                is_all = item.in_list(GROUP_OF_ALL)
                if item.in_list(source.player):
                    if is_all:
                        print_message(
                            source,
                            RText(tr('info.leave_list.header')).
                            h(tr('info.leave_list.hover')).
                            c(RAction.run_command, f'{PREFIX} leave {name}')
                        )
                    else:
                        print_message(
                            source,
                            RText(tr('info.leave.header')).
                            h(tr('info.leave.hover')).
                            c(RAction.run_command, f'{PREFIX} leave {name}')
                        )
                else:
                    if is_all:
                        print_message(
                            source,
                            RText(tr('info.join_list.header')).
                            h(tr('info.join_list.hover')).
                            c(RAction.run_command, f'{PREFIX} join {name}')
                        )
                    else:
                        print_message(
                            source,
                            RText(tr('info.join.header')).
                            h(tr('info.join.hover')).
                            c(RAction.run_command, f'{PREFIX} join {name}')
                        )
        print_message(source, tr('msg.text'))
        count = 0
        for msg in item.msg:
            count += 1
            print_message(
                source,
                f'[{str(count)}] ' +

                RText('[×] ', color=RColor.red).
                h(tr('msg.delete')).
                c(RAction.run_command, f'{PREFIX} del {name} {count}') +

                RText(f'[{disp_time(source, msg.time, tz)}] ', color=RColor.gray).
                h(format_time(source, msg.time, tz)) +

                player_RText(msg.sender, '<{}> ') +

                url_tr(msg.text).
                h(tr('msg.edit')).
                c(RAction.suggest_command, f'{PREFIX} edit {name} {count} {reverse_interpreter(msg.text) if source.is_player else msg.text}')
            )
        print_message(
            source,
            RText(tr('info.send.header')).
            h(tr('info.send.hover')).
            c(RAction.suggest_command, f'{PREFIX} send {name} ')
        )
    else:
        print_unknown(source, name)


@new_thread('make_group')
def make_group(source: CommandSource, name, perm: int, color: str):
    try:
        disp_name = RText(name, color=RColor.from_mc_value(color))
    except Exception as e:
        print_message(
            source,
            tr(
                'make_group.fail',
                RText(name, color=RColor.from_mc_value(config.default_color)),
                tr('command.invalid_color', color) + f' - {e}'
            )
        )
        server_inst.logger.exception('Failed to make group {}'.format(name))
        return
    if player_storage.contains(name):
        print_message(
            source,
            tr('make_group.exist.player', RText(name, color=player_storage.get(name).get_color())).
            h(tr('info.player')).
            c(RAction.run_command, f'{PREFIX} info {name}')
        )
        return
    if group_storage.contains(name):
        print_message(
            source,
            tr('make_group.exist.group', RText(name, color=group_storage.get(name).get_color())).
            h(tr('info.group')).
            c(RAction.run_command, f'{PREFIX} info {name}')
        )
        return
    if req_perm(source, perm):
        return
    try:
        group = Group(perm=perm, color=color)
        group_storage.add_item(name, group)
    except Exception as e:
        print_message(source, tr('make_group.fail', disp_name, e))
        server_inst.logger.exception('Failed to make group {}'.format(name))
    else:
        print_message(
            source,
            tr('make_group.success', disp_name).
            h(tr('info.group')).
            c(RAction.run_command, f'{PREFIX} info {name}')
        )


@new_thread('del_group')
def del_group(source: CommandSource, name):
    if group_storage.contains(name):
        if req_perm(source, group_storage.get(name).perm):
            return

        def confirm_del_group():
            try:
                item = group_storage.pop_item(name)
                for player_id in item.list:
                    if player_id == GROUP_OF_ALL:
                        handle_leave_all(source, name)
                    else:
                        player_storage.leave(player_id, name)


            except Exception as e:
                print_message(
                    source,
                    tr('del_group.fail', e).
                    h(tr('info.group')).
                    c(RAction.run_command, f'{PREFIX} info {name}')
                )
                server_inst.logger.exception('Failed to delete group {}'.format(name))
            else:
                print_message(
                    source,
                    tr('del_group.success', RText(name, color=item.get_color()))
                )

        confirm.req_confirm(source, confirm_del_group)
    else:
        print_unknown(source, name)


@new_thread('perm_group')
def perm_group(source: CommandSource, name, level: int):
    if group_storage.contains(name):
        if req_perm(source, level):
            return
        if req_perm(source, group_storage.get(name).perm):
            return
        try:
            group_storage.change_perm(name, level)
        except Exception as e:
            print_message(
                source,
                tr('perm_group.fail', e).
                h(tr('info.group')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
            server_inst.logger.exception('Failed to change permission of the group {}'.format(name))
        else:
            print_message(
                source,
                tr('perm_group.success', group_RText(name), level).
                h(tr('info.group')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
    else:
        print_unknown(source, name)


@new_thread('color_item')
def color_item(source: CommandSource, name, color: str):
    item = group_storage.get(name)
    if item is None:
        item = player_storage.get(name)
        item_type = 'player'
        if req_is_player(source, name):
            return
    else:
        item_type = 'group'
        if req_perm(source, group_storage.get(name).perm):
            return

    if item is not None:

        try:
            RColor.from_mc_value(color)
        except Exception as e:
            print_message(
                source,
                tr(
                    'color_item.fail',
                    tr('command.invalid_color', color) + f' - {e}'
                )
            )
            server_inst.logger.exception(f'Failed to change color of the {item_type} {name}')
            return

        try:
            if item_type == 'group':
                group_storage.change_color(name, color)
            else:
                player_storage.change_color(name, color)
        except Exception as e:
            print_message(
                source,
                tr('color_item.fail', e).
                h(tr(f'info.{item_type}')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
            server_inst.logger.exception(f'Failed to change color of the {item_type} {name}')
        else:
            print_message(
                source,
                tr(
                    f'color_item.success.{item_type}',
                    RText(name, RColor.from_mc_value(color)), RText(color, color=RColor.from_mc_value(color))
                ).
                h(tr(f'info.{item_type}')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
    else:
        print_unknown(source, name, 'group_or_player')


@new_thread('join_group')
def join_group(source: CommandSource, name, player_id=None):
    if group_storage.contains(name):
        if player_id is None:
            if isinstance(source, PlayerCommandSource):
                player_id = source.player
            else:
                player_id = config.default_sender

        if player_id == GROUP_OF_ALL:
            if req_perm(source, config.perm_to_modify_all):
                return
            handle_join_all(source, name)
            return
        if not player_storage.contains(player_id):
            print_unknown(source, player_id, 'player')
            return

        if req_perm(source, server_inst.get_permission_level(player_id)):
            return

        group = group_storage.get(name)

        if req_perm(source, group.perm):
            return

        try:
            is_all = group.in_list(GROUP_OF_ALL)
            group_join = group_storage.join(name, player_id)
            player_join = player_storage.join(player_id, name)
            if group_join and player_join and not is_all:
                print_message(source, tr('join_group.success', player_RText(player_id), group_RText(name)))
            elif group_join and not player_join and is_all:
                print_message(source, tr('join_group.is_all', player_RText(player_id), group_RText(name)))
            elif not group_join and not player_join:
                print_message(source, tr('join_group.exist', player_RText(player_id), group_RText(name)))
            else:
                print_message(source, tr('join_group.warn', player_RText(player_id), group_RText(name)))
        except Exception as e:
            print_message(source, tr('join_group.fail', player_RText(player_id), group_RText(name), e))
            server_inst.logger.exception('Failed to make {} join group {}'.format(player_id, name))
    else:
        print_unknown(source, name)


@new_thread('leave_group')
def leave_group(source: CommandSource, name, player_id=None):
    if group_storage.contains(name):
        if player_id is None:
            if isinstance(source, PlayerCommandSource):
                player_id = source.player
            else:
                player_id = config.default_sender

        if player_id == GROUP_OF_ALL:
            if req_perm(source, config.perm_to_modify_all):
                return
            handle_leave_all(source, name)
            return

        if req_perm(source, server_inst.get_permission_level(player_id)):
            return

        group = group_storage.get(name)
        player = player_storage.get(player_id)

        if req_perm(source, group.perm):
            return

        try:
            is_all = group.in_list(GROUP_OF_ALL)
            group_leave = group_storage.leave(name, player_id)
            player_in = player.in_list(name)
            if group_leave and player_in and not is_all:
                player_storage.leave(player_id, name)
                print_message(source, tr('leave_group.success', player_RText(player_id), group_RText(name)))
            elif group_leave and player_in and is_all:
                print_message(source, tr('leave_group.is_all_listed', player_RText(player_id), group_RText(name)))
            elif not group_leave and player_in and is_all:
                print_message(source, tr('leave_group.is_all_not_listed', player_RText(player_id), group_RText(name)))
            elif not group_leave and not player_in and not is_all:
                print_message(source, tr('leave_group.not_exist', player_RText(player_id), group_RText(name)))
            elif not group_leave and not player_in and is_all:
                print_message(source, tr('leave_group.warn_all', player_RText(player_id), group_RText(name)))
            else:
                player_storage.leave(player_id, name)
                print_message(source, tr('leave_group.warn', player_RText(player_id), group_RText(name)))
        except Exception as e:
            print_message(source, tr('leave_group.fail', player_RText(player_id), group_RText(name), e))
            server_inst.logger.exception('Failed to make {} leave group {}'.format(player_id, name))
    else:
        print_unknown(source, name)


@new_thread('send_msg')
def send_msg(source: CommandSource, name, msg: str):
    item = group_storage.get(name)
    if item is None:
        item = player_storage.get(name)
        item_type = 'player'
        storage = player_storage
    else:
        item_type = 'group'
        storage = group_storage

    if item is not None:
        try:
            if source.is_player:
                msg = interpreter(msg)
            if isinstance(source, PlayerCommandSource):
                storage.add_msg(name, source.player, msg)
            else:
                storage.add_msg(name, config.default_sender, msg)
        except Exception as e:
            print_message(
                source,
                tr(f'send_msg.fail', e).
                h(tr(f'info.{item_type}')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
            server_inst.logger.exception(f'Failed to leave msg to {item_type} {name}')
        else:
            print_message(
                source,
                tr(f'send_msg.success.{item_type}', RText(name, color=item.get_color())).
                h(tr(f'info.{item_type}')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
    else:
        print_unknown(source, name, 'group_or_player')


@new_thread('edit_msg')
def edit_msg(source: CommandSource, name, line: int, msg: str):
    item = group_storage.get(name)
    if item is None:
        item = player_storage.get(name)
        item_type = 'player'
        storage = player_storage
    else:
        item_type = 'group'
        storage = group_storage

    if item is not None:
        try:
            old_msg = item.msg[line - 1]
            if req_is_player(source, old_msg.sender):
                return

            if source.is_player:
                msg = interpreter(msg)

            storage.edit_msg(name, line - 1, msg)
        except Exception as e:
            print_message(
                source,
                tr(f'edit_msg.fail', e).
                h(tr(f'info.{item_type}')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
            server_inst.logger.exception(f'Failed to edit msg at {item_type} {name} line {line}')
        else:
            print_message(
                source,
                tr(f'edit_msg.success.{item_type}', RText(name, color=item.get_color()), line).
                h(tr(f'info.{item_type}')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
    else:
        print_unknown(source, name, 'group_or_player')


@new_thread('del_msg')
def del_msg(source: CommandSource, name, line: int):
    item = group_storage.get(name)
    if item is None:
        item = player_storage.get(name)
        item_type = 'player'
        storage = player_storage
    else:
        item_type = 'group'
        storage = group_storage

    if item is not None:
        def fail(e):
            print_message(
                source,
                tr(f'del_msg.fail', e).
                h(tr(f'info.{item_type}')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
            server_inst.logger.exception(f'Failed to delete msg at {item_type} {name} line {line}')

        try:
            old_msg = item.msg[line - 1]
            perm = item.perm

            if isinstance(source, PlayerCommandSource) and \
                    ((perm == -1 and source.player != name) or not source.has_permission(perm)) and \
                    source.player != old_msg.sender:
                source.reply(tr('command.permission_denied'))
                return

            def confirm_del_msg():
                try:
                    storage.del_msg(name, line - 1)
                except Exception as e:
                    fail(e)
                else:
                    print_message(
                        source,
                        tr(f'del_msg.success.{item_type}', RText(name, color=item.get_color()), line).
                        h(tr(f'info.{item_type}')).
                        c(RAction.run_command, f'{PREFIX} info {name}')
                    )

            confirm.req_confirm(source, confirm_del_msg)

        except Exception as e:
            fail(e)


    else:
        print_unknown(source, name, 'group_or_player')


def need_confirm(source: CommandSource):
    print_message(
        source,
        tr('confirm.need_confirm', PREFIX).
        h(tr('confirm.hover')).
        c(RAction.suggest_command, f'{PREFIX} confirm')
    )


def nothing_to_confirm(source: CommandSource):
    print_message(source, tr('confirm.nothing_to_confirm'))


@new_thread('place_group')
def place_group(source: CommandSource, name, pos):
    if group_storage.contains(name):
        if req_perm(source, group_storage.get(name).perm):
            return
        try:
            group_storage.place_item(name, pos - 1)
        except Exception as e:
            print_message(
                source,
                tr('place_group.fail', group_RText(name), e).
                h(tr('info.group')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
            server_inst.logger.exception('Failed to change position of the group {}'.format(name))
        else:
            print_message(
                source,
                tr('place_group.success', group_RText(name), pos).
                h(tr('info.group')).
                c(RAction.run_command, f'{PREFIX} info {name}')
            )
    else:
        print_unknown(source, name)


@new_thread('list_items')
def list_items(source: CommandSource, *, mode: str = 'search', keyword: Optional[str] = None, page: Optional[int] = None):
    tz = get_tz(source)
    matched_items: List[tuple] = []
    online_players = online_player_api.get_player_list()
    if mode == 'search':
        for name in player_storage.get_all_names():
            if name.find(keyword) != -1:
                if name in online_players:
                    player_storage.update_latest_online_time(name)
                player = player_storage.get(name)
                matched_items.append((name, player.color, player.latest_online_time))
        for name in group_storage.get_all_names():
            if name.find(keyword) != -1:
                matched_items.append((name, group_storage.get(name).color))
    else:
        storage: Storage
        if mode == 'list':
            group_storage.for_each(lambda n, value: matched_items.append((n, value.color)))
        elif mode == 'ids':
            for player_id in online_players:
                if player_storage.contains(player_id):
                    player_storage.update_latest_online_time(player_id)
                player_storage.update_latest_online_time(config.default_sender)
            player_storage.for_each(lambda n, value: matched_items.append((n, value.color, value.latest_online_time)))

    matched_count = len(matched_items)
    page_count = ceil(matched_count / config.item_per_page)

    def line(name: str, color: str, time: float = None):
        r = RTextList(
            RText(f'{name} ', color=RColor.from_mc_value(color)).
            h(tr(f'info.{"group" if time is None else "player"}')).
            c(RAction.run_command, f'{PREFIX} info {name}')
        )
        if time is not None:
            r.append(
                RText(disp_time(source, time, tz), color=RColor.gray).
                h(format_time(source, time, tz))
            )
        return r
    
    if page is None:
        for args in matched_items:
            print_message(source, line(*args), prefix=RText('- ', color=RColor.gray))
    else:
        if page > page_count:
            page = page_count
        left, right = (page - 1) * config.item_per_page, page * config.item_per_page
        for i in range(left, right):
            if 0 <= i < matched_count:
                print_message(source, line(*matched_items[i]), prefix=RText('- ', color=RColor.gray))

        has_prev = page != 1
        has_next = page != page_count
        color = {False: RColor.dark_gray, True: RColor.gray}
        if keyword is None:
            keyword = ''
        else:
            keyword += ' '

        prev_page = RText('<-', color=color[has_prev])
        if has_prev:
            prev_page.h(tr('list_item.page_prev.Y')). \
                c(RAction.run_command, f'{PREFIX} {mode} {keyword}{page - 1}')
        else:
            prev_page.h(tr('list_item.page_prev.N'))

        next_page = RText('->', color=color[has_next])
        if has_next:
            next_page.h(tr('list_item.page_next.Y')). \
                c(RAction.run_command, f'{PREFIX} {mode} {keyword}{page + 1}')
        else:
            next_page.h(tr('list_item.page_next.N'))

        source.reply(RTextList(
            prev_page,
            RText(f' §a{page}§r/§a{page_count} ').
            h(tr('list_item.change_page')).
            c(RAction.suggest_command, f'{PREFIX} {mode} {keyword}'),
            next_page
        ))

    print_message(source, tr(f'list_item.count.{mode}', matched_count))


@new_thread('check_msg')
def check_msg(source: CommandSource, mode: str = None, tell_player: str = None):
    if mode is None:
        mode = config.default_check_mode
    msgs: List[(str, Msg, int)] = []

    if tell_player is not None:
        player_id = tell_player
    elif isinstance(source, PlayerCommandSource):
        player_id = source.player
    else:
        player_id = config.default_sender

    if player_storage.contains(player_id):
        tz = get_tz(source)
        groups = group_storage.ordered_items(player_storage.get(player_id).list)
        for name in groups:
            group = group_storage.get(name)
            count = 0
            for msg in group.msg:
                count += 1
                msgs.append((name, msg, count))
        player = player_storage.get(player_id)
        count = 0
        for msg in player.msg:
            count += 1
            msgs.append((player_id, msg, count))

        if mode == 'time':
            msgs.sort(key=lambda elem: elem[1].time)

        print_message(source, tr('msg.text'), tell_player=tell_player)

        for name, msg, count in msgs:
            if name == player_id:
                disp_name = player_RText(player_id, '[{}] ')
            else:
                disp_name = group_RText(name, '[{}] ')

            print_message(
                source,

                RText('[×] ', color=RColor.red).
                h(tr('msg.delete')).
                c(RAction.run_command, f'{PREFIX} del {name} {count}') +

                disp_name +

                RText(f'[{disp_time(source, msg.time, tz)}] ', color=RColor.gray).
                h(format_time(source, msg.time, tz)) +

                player_RText(msg.sender, '<{}> ') +

                url_tr(msg.text).
                h(tr('msg.edit')).
                c(RAction.suggest_command, f'{PREFIX} edit {name} {count} {msg.text}'),

                tell_player=tell_player
            )

        print_message(source, tr('msg.count', len(msgs)), tell_player=tell_player)

    else:
        print_unknown(source, player_id, 'player')


@new_thread('player_logged')
def on_player_logged(server: PluginServerInterface, player_name: str, player_ip: str):
    if not player_storage.contains(player_name):
        player_storage.add_item(player_name, build_player(player_ip))
    player_storage.update_latest_online_time(player_name)
    check_msg(server.get_plugin_command_source(), tell_player=player_name)


@new_thread('player_left')
def on_player_left(server: PluginServerInterface, player):
    if player_storage.contains(player):
        player_storage.update_latest_online_time(player)


def register_command(server: PluginServerInterface):
    search_group = QuotableText('keyword'). \
        runs(lambda src, ctx: list_items(src, keyword=ctx['keyword'])). \
        then(Integer('page').runs(lambda src, ctx: list_items(src, keyword=ctx['keyword'], page=ctx['page'])))

    server.register_command(
        Literal(PREFIX).
        runs(print_help_message).
        then(Literal('all').runs(lambda src: list_items(src, mode='list'))).
        then(
            Literal('list').runs(lambda src: list_items(src, mode='list')).
            then(Integer('page').runs(lambda src, ctx: list_items(src, mode='list', page=ctx['page'])))
        ).
        then(
            Literal('ids').runs(lambda src: list_items(src, mode='ids')).
            then(Integer('page').runs(lambda src, ctx: list_items(src, mode='ids', page=ctx['page'])))
        ).
        then(Literal('search').then(search_group)).
        then(search_group).  # for lazy_man
        then(
            Literal('info').then(
                QuotableText('name').runs(lambda src, ctx: info(src, ctx['name']))
            )
        ).
        then(
            Literal('make').then(
                QuotableText('name').
                runs(lambda src, ctx: make_group(src, ctx['name'], config.default_perm, config.default_color)).
                then(
                    Integer('perm').
                    in_range(0, 4).
                    runs(lambda src, ctx: make_group(src, ctx['name'], ctx['perm'], config.default_color)).
                    then(
                        Text('color').
                        suggests(lambda: ['white', 'black']).
                        runs(lambda src, ctx: make_group(src, ctx['name'], ctx['perm'], ctx['color']))
                    )
                )
            )
        ).
        then(
            Literal('perm').then(
                QuotableText('name').then(
                    Integer('level').
                    in_range(0, 4).
                    runs(lambda src, ctx: perm_group(src, ctx['name'], ctx['level']))
                )
            )
        ).
        then(
            Literal('color').then(
                QuotableText('name').then(
                    Text('color').
                    suggests(lambda: ['white', 'black']).
                    runs(lambda src, ctx: color_item(src, ctx['name'], ctx['color']))
                )
            )
        ).
        then(
            Literal('join').then(
                QuotableText('name').
                runs(lambda src, ctx: join_group(src, ctx['name'])).
                then(
                    QuotableText('player_id').
                    runs(lambda src, ctx: join_group(src, ctx['name'], player_id=ctx['player_id']))
                )
            )
        ).
        then(
            Literal('leave').then(
                QuotableText('name').
                runs(lambda src, ctx: leave_group(src, ctx['name'])).
                then(
                    QuotableText('player_id').
                    runs(lambda src, ctx: leave_group(src, ctx['name'], player_id=ctx['player_id']))
                )
            )
        ).
        then(
            Literal('send').then(
                QuotableText('name').then(
                    GreedyText('msg').
                    runs(lambda src, ctx: send_msg(src, ctx['name'], ctx['msg']))
                )
            )
        ).
        then(
            Literal('edit').then(
                QuotableText('name').then(
                    Integer('line').
                    at_min(1).then(
                        GreedyText('msg').
                        runs(lambda src, ctx: edit_msg(src, ctx['name'], ctx['line'], ctx['msg']))
                    )
                )
            )
        ).
        then(
            Literal('del').then(
                QuotableText('name').
                runs(lambda src, ctx: del_group(src, ctx['name'])).
                then(
                    Integer('line').
                    at_min(1).
                    runs(lambda src, ctx: del_msg(src, ctx['name'], ctx['line']))
                )
            )
        ).
        then(
            Literal('place').then(
                QuotableText('name').then(
                    Integer('pos').
                    at_min(1).
                    runs(lambda src, ctx: place_group(src, ctx['name'], ctx['pos']))
                )
            )
        ).
        then(
            Literal('check').
            runs(lambda src: check_msg(src)).
            then(
                Literal('time').
                runs(lambda src: check_msg(src, mode='time'))
            ).
            then(
                Literal('group').
                runs(lambda src: check_msg(src, mode='group'))
            )
        ).
        then(
            Literal('confirm').
            runs(lambda src: confirm.apply_confirm(src))
        )
    )


def on_load(server: PluginServerInterface, old):
    global config, HelpMessage, server_inst, online_player_api, player_ip_logger
    server_inst = server
    meta = server.get_self_metadata()
    online_player_api = server.get_plugin_instance('online_player_api')
    player_ip_logger = server.get_plugin_instance('player_ip_logger')
    HelpMessage = tr('help_message', PREFIX, meta.name, meta.version)
    config = server.load_config_simple(CONFIG_FILE, target_class=Config)
    handle_get_storage()
    if old is not None:
        handle_config_change(config, old.config)
    register_command(server)
    server.register_help_message(PREFIX, command_run(tr('register.summary_help'), tr('register.show_help'), PREFIX))
    server.register_event_listener('player_ip_logger.player_login', on_player_logged)
