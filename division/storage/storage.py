from typing import List, Optional, Type, Callable
import bisect
from abc import ABCMeta, abstractmethod
import time

from mcdreforged.api.all import *


class Msg(Serializable):
    time: float
    sender: str
    text: str

    def set_sender(self, sender):
        self.sender = sender


class Item(Serializable, metaclass=ABCMeta):
    perm: int
    color: str
    msg: List[Msg] = []
    list: List[str] = []

    def get_color(self) -> RColor:
        from division.entry import config
        try:
            cl = RColor.from_mc_value(self.color)
        except Exception as e:
            cl = config.default_color
        return cl

    def add_msg(self, sender: str, text: str):
        self.msg.append(Msg(time=time.time(), sender=sender, text=text))

    def del_msg(self, idx: int):
        self.msg.pop(idx)

    def edit_msg(self, idx: int, text: str):
        self.msg[idx].text = text

    def for_each_msg(self, callback: Callable):
        for m in self.msg:
            callback(m)

    def in_list(self, value: str):
        idx = bisect.bisect_left(self.list, value)
        return idx < len(self.list) and self.list[idx] == value

    def join(self, value: str):
        if not self.in_list(value):
            bisect.insort_left(self.list, value)
            return True
        return False

    def leave(self, value: str):
        if self.in_list(value):
            self.list.pop(bisect.bisect_left(self.list, value))
            return True
        return False


class Group(Item):
    pass


class Player(Item):
    ip: str
    latest_online_time: float

    def update_latest_online_time(self):
        self.latest_online_time = time.time()


class OtherStorage(metaclass=ABCMeta):
    @abstractmethod
    def get_group_for_all(self) -> List[str]:
        pass

    @abstractmethod
    def add_group_for_all(self, name):
        pass

    @abstractmethod
    def remove_group_for_all(self, name):
        pass


class Storage(metaclass=ABCMeta):

    @abstractmethod
    def get(self, name: str) -> Optional[Item]:
        pass

    @abstractmethod
    def contains(self, name: str) -> bool:
        pass

    @abstractmethod
    def add_item(self, name: str, item: Item) -> bool:
        pass

    @abstractmethod
    def pop_item(self, name: str) -> Item:
        pass

    @abstractmethod
    def for_each(self, callback: Callable):
        pass

    @abstractmethod
    def change_perm(self, name: str, level: int):
        pass

    @abstractmethod
    def change_color(self, name: str, color: str):
        pass

    @abstractmethod
    def join(self, item, value) -> bool:
        pass

    @abstractmethod
    def leave(self, item, value) -> bool:
        pass

    @abstractmethod
    def add_msg(self, item, sender, text):
        pass

    @abstractmethod
    def edit_msg(self, item, line, text):
        pass

    @abstractmethod
    def del_msg(self, item, line):
        pass

    @abstractmethod
    def get_all_names(self) -> List[str]:
        pass

    @abstractmethod
    def ordered_items(self, item_list: List[str]) -> List[str]:
        pass

    @abstractmethod
    def place_item(self, name, pos):
        pass


class GroupStorage(metaclass=ABCMeta):
    pass


class PlayerStorage(metaclass=ABCMeta):
    @abstractmethod
    def update_latest_online_time(self, name):
        pass


def build_player(ip) -> Player:
    from division.entry import config
    try:
        from division.entry import other_storage
        player = Player(
            perm=-1,
            color=config.default_color,
            ip=ip,
            latest_online_time=time.time(),
            list=other_storage.get_group_for_all()
        )
    except Exception as e:
        player = Player(
            perm=-1,
            color=config.default_color,
            ip=ip,
            latest_online_time=time.time()
        )
    if config.msg_for_new_player != '':
        player.add_msg(config.default_sender, config.msg_for_new_player)
    return player


def build_other_storage(mode: str) -> OtherStorage:
    from division.entry import group_storage
    from division.storage.direct import DirectOtherStorage
    from division.storage.redis_s import RedisOtherStorage
    if mode == 'direct':
        return DirectOtherStorage(group_storage)
    elif mode == 'redis':
        return RedisOtherStorage()
