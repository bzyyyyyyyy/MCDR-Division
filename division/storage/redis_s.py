import json
import os
from threading import RLock
from typing import List, Optional, Type, Callable
from collections import OrderedDict
import time
import bisect
from abc import ABCMeta, abstractmethod
from redis import Redis
from rejson import Client, Path

from mcdreforged.api.all import *

from division.storage.storage import Storage, GroupStorage, PlayerStorage, OtherStorage, Item, Group, Player, Msg
from division.constants import GROUPS_STORAGE_FILE, PLAYERS_STORAGE_FILE, GROUP_OF_ALL


r: Redis
rj: Client


def init_redis(host: str, port: int, db: int, password: str | None):
    global r, rj
    r = Redis(host, port, db=db, password=password)
    rj = Client(host=host, port=port, db=db, password=password, decode_responses=True)



class RedisOtherStorage(OtherStorage):
    def __init__(self):
        if not r.exists('group_for_all'):
            rj.jsonset('group_for_all', Path.rootPath(), [])

    def get_group_for_all(self) -> List[str]:
        data = rj.jsonget('group_for_all', Path.rootPath())
        for i in range(len(data)):
            data[i] = data[i].encode('latin1').decode('utf-8')
        return data

    def add_group_for_all(self, name):
        rj.jsonarrappend('group_for_all', Path.rootPath(), name)

    def remove_group_for_all(self, name):
        rj.jsonarrpop('group_for_all', Path.rootPath(), rj.jsonarrindex('group_for_all', Path.rootPath(), name))


class RedisStorage(Storage, metaclass=ABCMeta):
    def __init__(self):
        if not r.exists(self.prefix):
            rj.jsonset(self.prefix, Path.rootPath(), [])
            self.first_load = True
        else:
            self.first_load = False

    @property
    @abstractmethod
    def prefix(self) -> str:
        pass

    @abstractmethod
    def get_item_type(self) -> Type:
        pass

    def get(self, name: str) -> Optional[Item]:
        data = rj.jsonget(self.prefix + name, Path.rootPath())
        if data is None:
            return None
        data = deserialize(data, self.get_item_type())
        for msg in data.msg:
            msg.text = msg.text.encode('latin1').decode('utf-8')
        if self.prefix == 'p-':
            for i in range(len(data.list)):
                data.list[i] = data.list[i].encode('latin1').decode('utf-8')
        return data

    def set(self, name: str, item: Item):
        if not self.contains(name):
            rj.jsonarrappend(self.prefix, Path.rootPath(), name)
        rj.jsonset(self.prefix + name, Path.rootPath(), serialize(item))

    def contains(self, name: str) -> bool:
        return bool(rj.exists(self.prefix + name)) and name in self.get_all_names()

    def add_item(self, name: str, item: Item) -> bool:
        if self.contains(name):
            return False
        self.set(name, item)
        return True

    def pop_item(self, name: str) -> Item:
        rj.jsonarrpop(self.prefix, Path.rootPath(), rj.jsonarrindex(self.prefix, Path.rootPath(), name))
        rst = self.get(name)
        rj.jsondel(self.prefix + name, Path.rootPath())
        return rst

    def for_each(self, callback: Callable):
        for name in self.get_all_names():
            item = self.get(name)
            callback(name, item)
            self.set(name, item)

    def change_perm(self, name: str, level: int):
        rj.jsonset(self.prefix + name, Path('.perm'), level)

    def change_color(self, name: str, color: str):
        rj.jsonset(self.prefix + name, Path('.color'), color)

    def join(self, item, value) -> bool:
        lst = rj.jsonget(self.prefix + item, Path('.list'))
        for i in range(len(lst)):
            lst[i] = lst[i].encode('latin1').decode('utf-8')
        idx = bisect.bisect_left(lst, value)
        if not (idx < len(lst) and lst[idx] == value):
            bisect.insort_left(lst, value)
            rj.jsonset(self.prefix + item, Path('.list'), lst)
            return True
        return False

    def leave(self, item, value) -> bool:
        lst = rj.jsonget(self.prefix + item, Path('.list'))
        for i in range(len(lst)):
            lst[i] = lst[i].encode('latin1').decode('utf-8')
        idx = bisect.bisect_left(lst, value)
        if idx < len(lst) and lst[idx] == value:
            lst.pop(bisect.bisect_left(lst, value))
            rj.jsonset(self.prefix + item, Path('.list'), lst)
            return True
        return False

    def add_msg(self, item, sender, text: str):
        msg = Msg(time=time.time(), sender=sender, text=text)
        rj.jsonarrappend(self.prefix + item, Path('.msg'), serialize(msg))

    def edit_msg(self, item, line, text):
        rj.jsonset(self.prefix + item, Path(f'.msg[{line}].text'), text)

    def del_msg(self, item, line):
        rj.jsonarrpop(self.prefix + item, Path(f'.msg'), line)

    def get_all_names(self) -> List[str]:
        data = rj.jsonget(self.prefix, Path.rootPath())
        for i in range(len(data)):
            data[i] = data[i].encode('latin1').decode('utf-8')
        return data

    def ordered_items(self, item_list: List[str]) -> List[str]:
        rst: List[str] = []
        for name in self.get_all_names():
            if name in item_list:
                rst.append(name)
        return rst

    def place_item(self, name, pos):
        if not self.contains(name):
            raise Exception('No such item')
        rj.jsonarrpop(self.prefix, Path.rootPath(), rj.jsonarrindex(self.prefix, Path.rootPath(), name))
        rj.jsonarrinsert(self.prefix, Path.rootPath(), pos, name)


class RedisGroupStorage(GroupStorage, RedisStorage):

    @property
    def prefix(self) -> str:
        return 'g-'

    def get_item_type(self) -> Type:
        return Group


class RedisPlayerStorage(PlayerStorage, RedisStorage):

    @property
    def prefix(self) -> str:
        return 'p-'

    def get_item_type(self) -> Type:
        return Player

    def add_item(self, name: str, item: Item) -> bool:
        if self.contains(name):
            return False
        if not self.contains(name):
            rj.jsonarrinsert(self.prefix, Path.rootPath(), 0, name)
        rj.jsonset(self.prefix + name, Path.rootPath(), serialize(item))
        return True

    def update_latest_online_time(self, name):
        rj.jsonset(self.prefix + name, Path('.latest_online_time'), time.time())
        player = rj.jsonarrpop(self.prefix, Path.rootPath(), rj.jsonarrindex(self.prefix, Path.rootPath(), name))
        rj.jsonarrinsert(self.prefix, Path.rootPath(), 0, player)
