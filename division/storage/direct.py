import json
import os
from threading import RLock
from typing import List, Optional, Type, Callable
from collections import OrderedDict
from abc import ABCMeta, abstractmethod

from mcdreforged.api.all import *

from division.storage.storage import Storage, GroupStorage, PlayerStorage, OtherStorage, Item, Group, Player
from division.constants import GROUPS_STORAGE_FILE, PLAYERS_STORAGE_FILE, GROUP_OF_ALL


class DirectOtherStorage(OtherStorage):
    def __init__(self, group_storage: Storage):
        self.group_for_all = []

        def check_group(name, group):
            if isinstance(group, Group):
                if group.in_list(GROUP_OF_ALL):
                    self.group_for_all.append(name)

        group_storage.for_each(check_group)

    def get_group_for_all(self) -> List[str]:
        return self.group_for_all

    def add_group_for_all(self, name):
        if name not in self.group_for_all:
            self.group_for_all.append(name)

    def remove_group_for_all(self, name):
        if name not in self.group_for_all:
            self.group_for_all.remove(name)


class DirectStorage(Storage, metaclass=ABCMeta):
    def __init__(self):
        self.items: OrderedDict[str, Item] = OrderedDict()
        self._lock = RLock()

    @abstractmethod
    def get_storage_file(self) -> str:
        pass

    @abstractmethod
    def get_item_type(self) -> Type:
        pass

    def get(self, name: str) -> Optional[Item]:
        with self._lock:
            return self.items.get(name)

    def contains(self, name: str) -> bool:
        with self._lock:
            return name in self.items

    def add_item(self, name: str, item: Item) -> bool:
        with self._lock:
            if self.contains(name):
                return False
            else:
                self.items[name] = item
                self._save()
                return True

    def pop_item(self, name: str) -> Item:
        with self._lock:
            r = self.items.pop(name, default=None)
            self._save()
            return r

    def for_each(self, callback: Callable):
        with self._lock:
            for item in self.items:
                callback(item, self.items[item])
            self._save()

    def change_perm(self, name: str, level: int):
        with self._lock:
            item = self.get(name)
            if not item:
                raise Exception('No such item')
            else:
                item.perm = level
                self._save()

    def change_color(self, name: str, color: str):
        with self._lock:
            item = self.get(name)
            if not item:
                raise Exception('No such item')
            else:
                item.color = color
                self._save()
                return True

    def join(self, item, value) -> bool:
        with self._lock:
            r = self.items.get(item).join(value)
            self._save()
            return r

    def leave(self, item, value) -> bool:
        with self._lock:
            r = self.items.get(item).leave(value)
            self._save()
            return r

    def add_msg(self, item, sender, text):
        with self._lock:
            self.items.get(item).add_msg(sender, text)
            self._save()

    def edit_msg(self, item, line, text):
        with self._lock:
            self.items.get(item).edit_msg(line, text)
            self._save()

    def del_msg(self, item, line):
        with self._lock:
            self.items.get(item).del_msg(line)
            self._save()

    def get_all_names(self) -> List[str]:
        with self._lock:
            return list(self.items.keys())

    def ordered_items(self, item_list: List[str]) -> List[str]:
        with self._lock:
            r: List[str] = []
            for name in self.items.keys():
                if name in item_list:
                    r.append(name)
            return r

    def place_item(self, name, pos):
        with self._lock:
            if self.contains(name) and pos < len(self.items):
                if pos < len(self.items)/2:
                    self.items.move_to_end(name, last=False)
                    for i in range(pos):
                        self.items.move_to_end(list(self.items.keys())[pos], last=False)
                else:
                    self.items.move_to_end(name, last=True)
                    for i in range(len(self.items) - pos - 1):
                        self.items.move_to_end(list(self.items.keys())[pos], last=True)
            else:
                raise IndexError

    def load(self, file_path: str) -> bool:
        with self._lock:
            folder = os.path.dirname(file_path)
            if not os.path.isdir(folder):
                os.makedirs(folder)
            self.items.clear()
            needs_overwrite = False
            if not os.path.isfile(file_path):
                needs_overwrite = True
            else:
                with open(file_path, 'r', encoding='utf8') as handle:
                    data = None
                    try:
                        data = json.load(handle)
                        items = deserialize(data, OrderedDict[str, self.get_item_type()])
                    except Exception as e:
                        from division.entry import server_inst
                        server_inst.logger.error(f'Fail to load {file_path}: {e}')
                        server_inst.logger.error(f'Unknown data: {data}')
                        needs_overwrite = True
                    else:
                        self.items = items
            if needs_overwrite:
                self._save()
        return needs_overwrite

    def _save(self):
        with self._lock:
            from division.entry import server_inst
            file_path = os.path.join(server_inst.get_data_folder(), self.get_storage_file())
            with open(file_path, 'w', encoding='utf8') as file:
                json.dump(serialize(self.items), file, indent=4, ensure_ascii=False)


class DirectGroupStorage(GroupStorage, DirectStorage):

    def get_storage_file(self) -> str:
        return GROUPS_STORAGE_FILE

    def get_item_type(self) -> Type:
        return Group


class DirectPlayerStorage(PlayerStorage, DirectStorage):

    def add_item(self, name: str, item: Item) -> bool:
        with self._lock:
            if self.contains(name):
                return False
            else:
                self.items[name] = item
                self.items.move_to_end(name, last=False)
                self._save()
                return True

    def get_storage_file(self) -> str:
        return PLAYERS_STORAGE_FILE

    def get_item_type(self) -> Type:
        return Player

    def update_latest_online_time(self, name):
        with self._lock:
            player = self.items.get(name)
            if isinstance(player, Player):
                player.update_latest_online_time()
            self.items.move_to_end(name, last=False)
            self._save()
