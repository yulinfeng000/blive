from collections import namedtuple
from multiprocessing import RawValue, Lock
import json
import requests
import struct
import enum
import brotli
import zlib


def get_blive_ws_url(roomid, ssl=False):
    resp = requests.get(
        f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={roomid}&platform=pc&player=web"
    )
    data = resp.json()
    url_obj = data["data"]["host_server_list"][1]
    if ssl:
        url = f"ws://{url_obj['host']}:{url_obj['ws_port']}/sub"
    else:
        url = f"wss://{url_obj['host']}:{url_obj['wss_port']}/sub"
    return url, data["data"]["token"]


def get_blive_room_info(roomid):
    """
    得到b站直播间id,（短id不是真实的id）

    Return: ture_id,short_id,up_id
    """
    resp = requests.get(
        "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom",
        params={"room_id": roomid},
    )
    data = resp.json()
    return (
        data["data"]["room_info"]["room_id"],
        data["data"]["anchor_info"]["base_info"]["uname"],
    )


def get_blive_dm_history(roomid):
    resp = requests.post(
        "https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory",
        headers={
            "Host": "api.live.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0",
        },
        data={
            "roomid": roomid,
            "csrf_token": "",
            "csrf": "",
            "visit_id": "",
        },
    )
    return resp.json()


def certification(roomid, token, uid=0, protover=1, platform="web"):
    return {
        "uid": uid,
        "roomid": roomid,
        "protover": protover,
        "platform": platform,
        "type": 2,
        "clientver": "1.4.3",
        "key": token,
    }


def heartbeat():
    return {}


class AuthReplyCode(enum.IntEnum):
    OK = 0
    TOKEN_ERROR = -101


# WS_BODY_PROTOCOL_VERSION
class ProtocolVersion(enum.IntEnum):
    NORMAL = 0  # 未压缩
    HEARTBEAT = 1  # 心跳
    DEFLATE = 2  # zlib压缩
    BROTLI = 3  # brotil 压缩


class Operation(enum.IntEnum):
    HEARTBEAT = 2  # 心跳
    HEARTBEAT_REPLY = 3  # 心跳回应
    NOTIFY = 5  # 通知
    AUTH = 7  # # 认证
    AUTH_REPLY = 8  # 认证回应


class Counter(object):
    # 线程安全计数器
    def __init__(self, init_value) -> None:
        self.current = RawValue("i", init_value)
        self.lock = Lock()

    def increment(self):
        with self.lock:
            self.current.value += 1

    def value(self):
        with self.lock:
            return self.current.value

    def increment_get(self):
        with self.lock:
            self.current.value += 1
            return self.current.value

    def get_increment(self):
        with self.lock:
            yield self.current.value
            self.current.value += 1


PackageHeader = namedtuple(
    "PackageHeader",
    ["package_size", "header_size", "version", "operation", "sequence_id"],
)

HeaderStruct = struct.Struct(">I2H2I")


class B_MsgPackage:
    def __init__(self) -> None:
        self.sequence = Counter(0)

    def pack(self, data, operation, version=ProtocolVersion.NORMAL):
        body = json.dumps(data).encode("utf-8")
        header = HeaderStruct.pack(
            *PackageHeader(
                package_size=HeaderStruct.size + len(body),
                header_size=HeaderStruct.size,
                version=version,
                operation=operation,
                sequence_id=self.sequence.increment_get(),
            )
        )
        return header + body

    def unpack(self, data) -> list:
        packages = []
        header = PackageHeader(*HeaderStruct.unpack(data[:16]))  #
        data = data[header.header_size :]

        # 心跳包处理
        if header.operation == Operation.HEARTBEAT_REPLY:
            # 心跳不会粘包
            packages.append((header, data[4:].decode("utf-8")))

        # 通知包处理
        elif header.operation == Operation.NOTIFY:

            def notify_pk_process(data):
                # 粘包处理代码 ,抽取为公共函数
                header = PackageHeader(*HeaderStruct.unpack(data[:16]))  # 包头
                if len(data) > header.package_size:  # 如果数据大小大于包头，说明是粘包
                    while True:
                        # 先把第一个包放进去
                        packages.append(
                            (header, data[16 : header.package_size].decode("utf-8"))
                        )
                        # 移动到下一个包
                        data = data[header.package_size :]
                        header = PackageHeader(*HeaderStruct.unpack(data[:16]))

                        if len(data) > header.package_size:
                            # 如果数据还大于package，说明还有1个以上的包
                            continue
                        else:
                            packages.append(
                                (header, data[16:].decode("utf-8"))
                            )  # 直接放第二个包
                            break
                else:
                    packages.append((header, data[16:].decode("utf-8")))

            # NOTIFY 消息可能会粘包
            if header.version == ProtocolVersion.DEFLATE:
                # 先zlib解码
                data = zlib.decompress(data)
                notify_pk_process(data)

            elif header.version == ProtocolVersion.BROTLI:
                # 与zlib 逻辑相同，先解码，然后数据可能要拆包
                data = brotli.decompress(data)
                notify_pk_process(data)

            elif header.version == ProtocolVersion.NORMAL:
                # normal 直接decode，feature
                packages.append((header, data.decode("utf-8")))
            else:
                # TODO 抛出错误或者打印日志
                pass

        elif header.operation == Operation.AUTH_REPLY:
            packages.append((header, data.decode("utf-8")))

        return packages


packman = B_MsgPackage()


class Events(str, enum.Enum):
    PREPARING = "PREPARING"  # 下播【结束语】
    ROOM_CHANGE = "ROOM_CHANGE"  # 房间信息改变
    ROOM_RANK = "ROOM_RANK"  # 排名改变
    DANMU_MSG = "DANMU_MSG"  # 接收到弹幕【自动回复】
    SEND_GIFT = "SEND_GIFT"  # 有人送礼【答谢送礼】
    WELCOME_GUARD = "WELCOME_GUARD"  # 舰长进入（不会触发）
    ENTRY_EFFECT = "ENTRY_EFFECT"  # 舰长、高能榜、老爷进入【欢迎舰长】
    WELCOME = "WELCOME"  # 老爷进入
    INTERACT_WORD = "INTERACT_WORD"  # 用户进入【欢迎】
    ATTENTION = "ATTENTION"  # 用户关注【答谢关注】
    SHARE = "SHARE"  # 用户分享直播间
    SPECIAL_ATTENTION = "SPECIAL_ATTENTION"  # 特别关注直播间，可用%special%判断
    ROOM_REAL_TIME_MESSAGE_UPDATE = "ROOM_REAL_TIME_MESSAGE_UPDATE"  # 粉丝数量改变
    SUPER_CHAT_MESSAGE = "SUPER_CHAT_MESSAGE"  # 醒目留言
    SUPER_CHAT_MESSAGE_JPN = "SUPER_CHAT_MESSAGE_JPN"  # 醒目留言日文翻译
    SUPER_CHAT_MESSAGE_DELETE = "SUPER_CHAT_MESSAGE_DELETE"  # 删除醒目留言
    ROOM_BLOCK_MSG = "ROOM_BLOCK_MSG"  # 用户被禁言，%uname%昵称
    GUARD_BUY = "GUARD_BUY"  # 有人上船
    FIRST_GUARD = "FIRST_GUARD"  # 用户初次上船
    # 船员数量改变事件，%uname%新船员昵称，%num%获取大航海数量，附带直播间信息json数据
    NEW_GUARD_COUNT = "NEW_GUARD_COUNT"
    USER_TOAST_MSG = "USER_TOAST_MSG"  # 上船附带的通知
    HOT_RANK_CHANGED = "HOT_RANK_CHANGED"  # 热门榜排名改变
    HOT_RANK_SETTLEMENT = "HOT_RANK_SETTLEMENT"  # 荣登热门榜topX
    HOT_RANK = "HOT_RANK"  # 热门榜xx榜topX，%text%获取排名
    ONLINE_RANK_V2 = "ONLINE_RANK_V2"  # 礼物榜（高能榜）刷新
    ONLINE_RANK_TOP3 = "ONLINE_RANK_TOP3"  # 高能榜TOP3改变
    ONLINE_RANK_COUNT = "ONLINE_RANK_COUNT"  # 高能榜改变
    NOTICE_MSG = "NOTICE_MSG"  # 上船等带的通知
    COMBO_SEND = "COMBO_SEND"  # 礼物连击
    SPECIAL_GIFT = "SPECIAL_GIFT"  # 定制的专属礼物
    ANCHOR_LOT_CHECKSTATUS = "ANCHOR_LOT_CHECKSTATUS"  # 天选时刻前的审核
    ANCHOR_LOT_START = "ANCHOR_LOT_START"  # 开启天选
    ANCHOR_LOT_END = "ANCHOR_LOT_END"  # 天选结束
    ANCHOR_LOT_AWARD = "ANCHOR_LOT_AWARD"  # 天选结果推送
    VOICE_JOIN_ROOM_COUNT_INFO = "VOICE_JOIN_ROOM_COUNT_INFO"  # 	申请连麦队列变化
    VOICE_JOIN_LIST = "VOICE_JOIN_LIST"  # 连麦申请、取消连麦申请
    VOICE_JOIN_STATUS = "VOICE_JOIN_STATUS"  # 开始连麦、结束连麦
    WARNING = "WARNING"  # 被警告，%text%可获取内容
    CUT_OFF = "CUT_OFF"  # 被超管切断
    room_admin_entrance = "room_admin_entrance"  # 设置房管
    ROOM_ADMINS = "ROOM_ADMINS"  # 房管数量改变
    # 勋章升级，仅送礼物后触发，需设置中开启“监听勋章升级”。%medal_level%获取新等级（但用户当前勋章不一定是本直播间）
    MEDAL_UPGRADE = "MEDAL_UPGRADE"
    STOP_LIVE_ROOM_LIST = "STOP_LIVE_ROOM_LIST"  # 停止直播的房间
    WIDGET_BANNER = "WIDGET_BANNER"  # 小部件横幅
    PK_BATTLE_PROCESS_NEW = "PK_BATTLE_PROCESS_NEW"  # 开始pk
    PK_BATTLE_PROCESS = "PK_BATTLE_PROCESS"  # pk
    COMMON_NOTICE_DANMAKU = "COMMON_NOTICE_DANMAKU"  # 弹幕通知
    HOT_RANK_CHANGED_V2 = "HOT_RANK_CHANGED_V2"  # 热门榜改变v2
    PK_BATTLE_SETTLE = "PK_BATTLE_SETTLE"  # pk结果
    PK_BATTLE_PRE_NEW = "PK_BATTLE_PRE_NEW"  # pk预创建
