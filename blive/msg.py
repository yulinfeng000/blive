from abc import ABC
import json

"""
消息操作封装类,目前只封装了弹幕消息操作
"""


class BaseMsg(ABC):
    def __init__(self, body) -> None:
        super().__init__()
        self.body = body

    def cmd(self):
        return self.body["cmd"]

    def info(self):
        return self.body["info"]

    def __repr__(self) -> str:
        return json.dumps(self.body)


class DanMuMsg(BaseMsg):
    def __init__(self, body) -> None:
        super(DanMuMsg, self).__init__(body)

    def content(self):
        return self.info()[1]

    def sender(self):
        return {"id": self.body["info"][2][0], "name": self.body["info"][2][1]}

    def timestamp(self):
        return self.body["info"][9]
