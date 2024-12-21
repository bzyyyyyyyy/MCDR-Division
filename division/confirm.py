from typing import Callable, Dict
import time

from mcdreforged.api.all import *


class Confirm:
    def __init__(self):
        self.req: Dict[str, tuple] = {}

    @new_thread('req_confirm')
    def req_confirm(self, source: CommandSource, callback: Callable):
        from division.entry import config, need_confirm
        if isinstance(source, PlayerCommandSource):
            key = source.player
        else:
            key = config.default_sender
        t = time.time()
        self.req[key] = t, callback
        need_confirm(source)
        while True:
            if key not in self.req:
                return
            if self.req[key][0] != t:
                return
            if self.req[key][0] + 60 < time.time():  # confirm in 1 min
                self.req.pop(key)
                return
            time.sleep(1)

    def apply_confirm(self, source: CommandSource):
        from division.entry import config, nothing_to_confirm
        key: str
        if isinstance(source, PlayerCommandSource):
            key = source.player
        else:
            key = config.default_sender
        try:
            t, callback = self.req.pop(key)
            callback()
        except Exception as e:
            nothing_to_confirm(source)
