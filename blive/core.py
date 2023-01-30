from collections import namedtuple
import json
from random import randint
import struct
import enum
import brotli
import zlib
from aiohttp import ClientSession


async def get_blive_ws_url(roomid,aio_session:ClientSession,ssl=True, platform="pc", player="web"):
    async with aio_session.get(
        f"https://api.live.bilibili.com/room/v1/Danmu/getConf",
        params={"room_id": roomid, "platform": platform, "player": player},
    ) as resp:
        data = await resp.json()
        lens = len(data["data"]["host_server_list"])
        url_obj = data["data"]["host_server_list"][randint(0, lens - 1)]
        if ssl:
            url = f"wss://{url_obj['host']}:{url_obj['wss_port']}/sub"
        else:
            url = f"ws://{url_obj['host']}:{url_obj['ws_port']}/sub"
        return url, data["data"]["token"]


async def get_blive_room_info(roomid,aio_session:ClientSession):
    """
    得到b站直播间id,(短id不是真实的id)

    Return: true_room_id,up_name
    """
    async with aio_session.get(
        "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom",
        params={"room_id": roomid},
    ) as resp:
        data = await resp.json()
        return (
            data["data"]["room_info"]["room_id"],
            data["data"]["anchor_info"]["base_info"]["uname"],
        )


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


PackageHeader = namedtuple(
    "PackageHeader",
    ["package_size", "header_size", "version", "operation", "sequence_id"],
)

HeaderStruct = struct.Struct(">I2H2I")


def counter(start=1):
    while True:
        yield start
        start += 1
       



class BLiveMsgPackage:
    """bilibili websocket message package"""

    def __init__(self) -> None:
        self.sequence = counter(0)

    def pack(self, data, operation, version=ProtocolVersion.NORMAL):
        body = json.dumps(data).encode("utf-8")
        header = HeaderStruct.pack(
            *PackageHeader(
                package_size=HeaderStruct.size + len(body),
                header_size=HeaderStruct.size,
                version=version,
                operation=operation,
                sequence_id=next(self.sequence),
            )
        )
        return header + body

    def zipped_notify_pkg_process(
        self, packages: list, data
    ):  # 解压后的包处理代码 ,抽取为公共函数, data: 解压后的原始数据
        header = PackageHeader(*HeaderStruct.unpack(data[:16]))  # 读取包头
        if len(data) > header.package_size:  # 如果数据大小大于包头声明的大小，说明是粘包
            while True:
                # 先把第一个包放进去 / 放入包
                packages.append(
                    (header, data[16 : header.package_size].decode("utf-8"))
                )
                # 移动到下一个包
                data = data[header.package_size :]
                # 读取下一个包的包头
                header = PackageHeader(*HeaderStruct.unpack(data[:16]))
                if len(data) > header.package_size:
                    # 如果数据还大于声明的package_size，说明还有1个以上的包
                    continue
                else:
                    # 剩下的数据刚好就是一个包,直接放，然后退出循环
                    packages.append((header, data[16:].decode("utf-8")))  # 直接放第二个包
                    break
        else:
            # 如果数据大小不大于包头声明的大小,说明是单个包太大压缩的。直接放入
            packages.append((header, data[16:].decode("utf-8")))

    def unpack(self, data) -> list:
        packages = []  # 装处理好的数据包用
        header = PackageHeader(*HeaderStruct.unpack(data[:16]))  # 读取数据包的头部
        data = data[16:]  # 读取数据包的数据段

        # 心跳包处理
        if header.operation == Operation.HEARTBEAT_REPLY:
            # 心跳不会粘包,前4位有不明含义的数据
            packages.append((header, data[4:].decode("utf-8")))

        # 通知包处理
        elif header.operation == Operation.NOTIFY:

            # NOTIFY 消息可能会粘包
            if header.version == ProtocolVersion.DEFLATE:
                # 先zlib解码，拆包
                data = zlib.decompress(data)
                self.zipped_notify_pkg_process(packages, data)

            elif header.version == ProtocolVersion.BROTLI:
                # 与 zlib 逻辑相同，先解码，然后数据可能要拆包
                data = brotli.decompress(data)
                self.zipped_notify_pkg_process(packages, data)

            elif header.version == ProtocolVersion.NORMAL:
                # normal 直接decode
                packages.append((header, data.decode("utf-8")))
            else:
                # TODO 抛出错误或者打印日志
                pass

        elif header.operation == Operation.AUTH_REPLY:
            packages.append((header, data.decode("utf-8")))

        return packages


packman = BLiveMsgPackage()


class Events(str, enum.Enum):
    LIVE = "LIVE"  # 主播开播
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
    NEW_GUARD_COUNT = (
        "NEW_GUARD_COUNT"  # 船员数量改变事件，%uname%新船员昵称，%num%获取大航海数量，附带直播间信息json数据
    )
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
    VOICE_JOIN_ROOM_COUNT_INFO = "VOICE_JOIN_ROOM_COUNT_INFO"  # 申请连麦队列变化
    VOICE_JOIN_LIST = "VOICE_JOIN_LIST"  # 连麦申请、取消连麦申请
    VOICE_JOIN_STATUS = "VOICE_JOIN_STATUS"  # 开始连麦、结束连麦
    WARNING = "WARNING"  # 被警告，%text%可获取内容
    CUT_OFF = "CUT_OFF"  # 被超管切断
    room_admin_entrance = "room_admin_entrance"  # 设置房管
    ROOM_ADMINS = "ROOM_ADMINS"  # 房管数量改变
    MEDAL_UPGRADE = "MEDAL_UPGRADE"  # 勋章升级，仅送礼物后触发，需设置中开启“监听勋章升级”。%medal_level%获取新等级（但用户当前勋章不一定是本直播间）
    STOP_LIVE_ROOM_LIST = "STOP_LIVE_ROOM_LIST"  # 停止直播的房间（这些房间会关闭ws连接）
    WIDGET_BANNER = "WIDGET_BANNER"  # 小部件横幅
    PK_BATTLE_PROCESS_NEW = "PK_BATTLE_PROCESS_NEW"  # 开始pk
    PK_BATTLE_PROCESS = "PK_BATTLE_PROCESS"  # pk
    COMMON_NOTICE_DANMAKU = "COMMON_NOTICE_DANMAKU"  # 弹幕通知
    HOT_RANK_CHANGED_V2 = "HOT_RANK_CHANGED_V2"  # 热门榜改变v2
    PK_BATTLE_SETTLE = "PK_BATTLE_SETTLE"  # pk结果
    PK_BATTLE_PRE_NEW = "PK_BATTLE_PRE_NEW"  # pk预创建
    LIVE_INTERACTIVE_GAME = "LIVE_INTERACTIVE_GAME"  # 在线互动游戏 送礼物参与
