from abc import ABC
import json

"""
消息操作封装类,目前只封装了弹幕消息操作
"""


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
        return {
            "id": self.body["info"][2][0],
            "name": self.body["info"][2][1],
            "medal": {
                "medal_name": self.body["info"][3][1] if self.body["info"][3] else "",
                "medal_level": self.body["info"][3][0] if self.body["info"][3] else 0,
            },
        }

    @property
    def timestamp(self):
        return self.body["info"][9]


class InteractWordMsg(BaseMsg):
    def __init__(self, body) -> None:
        super().__init__(body)

    @property
    def user(self):
        return {
            "id": self.body["data"]["uid"],
            "name": self.body["data"]["uname"],
            "medal": {
                "medal_name": self.body["data"]["fans_medal"]["medal_name"],
                "medal_level": self.body["data"]["fans_medal"]["medal_level"],
            },
        }

    @property
    def timestamp(self):
        return self.body["data"]["timestamp"]


class StopLiveRoomListMsg(BaseMsg):
    def __init__(self, body) -> None:
        super().__init__(body)

    @property
    def room_id_list(self):
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
        return {
            "id": self.body["data"]["uid"],
            "name": self.body["data"]["uname"],
            "medal": {
                "medal_name": self.body["data"]["medal_info"]["medal_name"],
                "medal_level": self.body["data"]["medal_info"]["medal_level"],
            },
        }

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
        return {
            "id": self.body["data"]["user_info"]["uname"],
            "name": self.body["data"]["uid"],
            "medal": {
                "medal_name": self.body["data"]["medal_info"]["medal_name"],
                "medal_level": self.body["data"]["medal_info"]["medal_level"],
            },
        }

    @property
    def price(self):
        return self.body["data"]["price"]

    @property
    def start_time(self):
        return self.body["data"]["start_time"]

    @property
    def time(self):
        return self.body["data"]["time"]
