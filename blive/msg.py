from abc import ABC
import json
from typing import List

"""
消息操作封装类,目前只封装了弹幕消息操作
"""


class DictObject:
    def __getitem__(self, idx):
        return getattr(self, idx)

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def __delitem__(self, k):
        delattr(self, k)


class Medal(DictObject):
    def __init__(self, medal_name, medal_level) -> None:
        super(DictObject, self).__init__()
        self.medal_name = medal_name
        self.medal_level = medal_level


class Sender(DictObject):
    def __init__(self, id, name, medal_name, medal_level) -> None:
        super(DictObject, self).__init__()
        self.id = id
        self.name = name
        self.medal = Medal(medal_name, medal_level)


class BaseMsg(ABC):
    def __init__(self, body) -> None:
        super().__init__()
        self.body = body

    @property
    def cmd(self):
        return self.body["cmd"]

    def __repr__(self) -> str:
        return json.dumps(self.body)


class DanMuMsg(BaseMsg):
    def __init__(self, body) -> None:
        super(DanMuMsg, self).__init__(body)

    @property
    def content(self):
        return self.body["info"][1]

    @property
    def sender(self):
        if not hasattr(self, "_sender"):
            self._sender = Sender(
                id=self.body["info"][2][0],
                name=self.body["info"][2][1],
                medal_name=self.body["info"][3][1] if self.body["info"][3] else "",
                medal_level=self.body["info"][3][0] if self.body["info"][3] else 0,
            )
        return self._sender

    @property
    def timestamp(self):
        return self.body["info"][9]


class InteractWordMsg(BaseMsg):
    def __init__(self, body) -> None:
        super().__init__(body)

    @property
    def user(self):
        if not hasattr(self, "_user"):
            self._user = Sender(
                id=self.body["data"]["uid"],
                name=self.body["data"]["uname"],
                medal_name=self.body["data"]["fans_medal"]["medal_name"],
                medal_level=self.body["data"]["fans_medal"]["medal_level"],
            )
        return self._user

    @property
    def timestamp(self):
        return self.body["data"]["timestamp"]


class StopLiveRoomListMsg(BaseMsg):
    def __init__(self, body) -> None:
        super().__init__(body)

    @property
    def room_id_list(self) -> List[int]:
        return self.body["data"]["room_id_list"]


class HotRankChangeV2Msg(BaseMsg):
    def __init__(self, body) -> None:
        super().__init__(body)

    @property
    def area_name(self):
        return self.body["data"]["area_name"]

    @property
    def rank_desc(self):
        return self.body["data"]["rank_desc"]

    @property
    def rank(self):
        return self.body["data"]["rank"]

    @property
    def trend(self):
        return self.body["data"]["trend"]

    @property
    def timestamp(self):
        return self.body["data"]["timestamp"]


class SendGiftMsg(BaseMsg):
    # TODO 礼物逻辑复杂, 考虑更复杂的封装类
    def __init__(self, body) -> None:

        super().__init__(body)

    @property
    def sender(self):
        if not hasattr(self, "_sender"):
            self._sender = Sender(
                id=self.body["data"]["uid"],
                name=self.body["data"]["uname"],
                medal_name=self.body["data"]["medal_info"]["medal_name"],
                medal_level=self.body["data"]["medal_info"]["medal_level"],
            )
        return self._sender

    @property
    def action(self):
        return self.body["data"]["action"]

    @property
    def gift(self):
        return {
            "gift_id": self.body["data"]["giftId"],
            "gift_name": self.body["data"]["giftName"],
            "gift_type": self.body["data"]["giftType"],
        }

    @property
    def combo(self):
        return {
            "batch_combo_id": self.body["data"]["batch_combo_id"],
            "batch_combo_send": self.body["data"]["batch_combo_send"],
            "combo_resources_id": self.body["data"]["combo_resources_id"],
            "combo_send": self.body["data"]["combo_send"],
            "combo_stay_time": self.body["data"]["combo_stay_time"],
            "combo_total_coin": self.body["data"]["combo_total_coin"],
        }


class SuperChatMsg(BaseMsg):
    def __init__(self, body) -> None:
        super().__init__(body)

    @property
    def content(self):
        return self.body["data"]["message"]

    @property
    def sender(self):
        if not hasattr(self, "_sender"):
            self._sender = Sender(
                id=self.body["data"]["user_info"]["uname"],
                name=self.body["data"]["uid"],
                medal_name=self.body["data"]["medal_info"]["medal_name"],
                medal_level=self.body["data"]["medal_info"]["medal_level"],
            )
        return self._sender

    @property
    def price(self):
        return self.body["data"]["price"]

    @property
    def start_time(self):
        return self.body["data"]["start_time"]

    @property
    def time(self):
        return self.body["data"]["time"]


class EntryEffectMsg(BaseMsg):
    def __init__(self, body) -> None:
        super().__init__(body)

    @property
    def uid(self):
        return self.body["data"]["uid"]

    @property
    def face(self):
        return self.body["data"]["face"]

    @property
    def copy_writting(self):
        return self.body["data"]["copy_writing"]

    @property
    def web_basemap_url(self):
        return self.body["data"]["web_basemap_url"]

    @property
    def basemap_url(self):
        return self.body["data"]["basemap_url"]


class LiveInteractiveGameMsg(BaseMsg):
    def __init__(self, body) -> None:
        super().__init__(body)

    @property
    def uid(self):
        return self.body["data"]["uid"]

    @property
    def uname(self):
        return self.body["data"]["uname"]

    @property
    def uface(self):
        return self.body["data"]["uface"]

    @property
    def fans_medal_level(self):
        return self.body["data"]["fans_medal_level"]

    @property
    def guard_level(self):
        return self.body["data"]["guard_level"]

    @property
    def gift(self):
        return {
            "gift_id": self.body["data"]["gift_id"],
            "gift_name": self.body["data"]["gift_name"],
            "gift_num": self.body["data"]["gift_num"],
            "price": self.body["data"]["price"],
            "paid": self.body["data"]["paid"],
        }

    def timestamp(self):
        return self.body["data"]["timestamp"]


class OnlineRankCountMsg(BaseMsg):
    def __init__(self, body) -> None:
        super().__init__(body)

    @property
    def count(self):
        return self.body["data"]["count"]
