import sys
import json
import asyncio
from typing import Awaitable, Dict, List, Tuple, Union
import loguru
import aiohttp
from aiohttp.client_ws import ClientWebSocketResponse
from aiohttp.http_websocket import WSMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.util import _Undefined

from .core import (
    packman,
    Events,
    Operation,
    PackageHeader,
    get_blive_room_info,
    get_blive_ws_url,
    certification,
    heartbeat,
)


undefined = _Undefined()


class BLiverCtx(object):
    def __init__(self, bliver, msg) -> None:
        super().__init__()
        self.ws: ClientWebSocketResponse = bliver.ws
        self.msg: Tuple = msg  # 原始消息
        self.bliver: BLiver = bliver
        self.body: Dict = None  # 消息内容


class Channel:
    """
    消息类型,不直接用list代替的原因是方便后面加入middleware类
    """

    def __init__(self) -> None:
        self.listeners = []

    def register_handler(self, handler):
        self.listeners.append(handler)

    def __getitem__(self, idx):
        return self.listeners.__getitem__(idx)

    def __iter__(self):
        return iter(self.listeners)


class Processor:
    def __init__(self, logger=None) -> None:
        self.logger = logger or loguru.logger
        self.channels: Dict[str, Channel] = {}
        for e in Events:
            self.channels[e] = Channel()

    def register(self, channel: str, handler: Awaitable):
        channel = self.channels[channel]
        channel.register_handler(handler)

    async def process(self, ctx):
        header: PackageHeader = ctx.msg[0]
        if header.operation == Operation.NOTIFY:
            msg = json.loads(ctx.msg[1])
            ctx.body = msg
            listeners = self.channels.get(msg["cmd"], [])  # 根据cmd 得到相应的处理句柄
            return await asyncio.gather(*[f(ctx) for f in listeners])


class BLiver:
    def __init__(self, roomid, logger=None, log_level="INFO"):
        self.roomid = roomid
        self.real_roomid, self.uname = get_blive_room_info(roomid)
        if not logger:
            self.logger = loguru.logger
            self.logger.remove()
            self.logger.add(sys.stderr, level=log_level)
        else:
            self.logger = logger
        self._ws: ClientWebSocketResponse = None
        self.scheduler = AsyncIOScheduler(timezone="Asia/ShangHai")
        self.processor = Processor(logger=self.logger)

    def on(self, event: Union[Events, List[Events]]):
        def f_wrapper(func):
            self.logger.debug("handler added,{}", func)
            if isinstance(event, list):
                for e in event:
                    self.processor.register(e, func)
            else:
                self.processor.register(event, func)
            return func

        return f_wrapper

    def register_handler(self, event: Union[Events, List[Events]], handler):
        self.processor.register(event, handler)

    def scheduled(
        self,
        trigger,
        args=None,
        kwargs=None,
        id=None,
        name=None,
        misfire_grace_time=undefined,
        coalesce=undefined,
        max_instances=undefined,
        next_run_time=undefined,
        jobstore="default",
        executor="default",
        **trigger_args,
    ):
        def s_func_wrapper(func):
            self.logger.debug("scheduler job added,{}", func)
            self.scheduler.add_job(
                func,
                trigger=trigger,
                args=args,
                kwargs=kwargs,
                id=id,
                name=name,
                misfire_grace_time=misfire_grace_time,
                coalesce=coalesce,
                max_instances=max_instances,
                next_run_time=next_run_time,
                jobstore=jobstore,
                executor=executor,
                replace_existing=True,
                **trigger_args,
            )
            return func

        return s_func_wrapper

    @property
    def ws(self):
        assert self._ws is not None
        return self._ws

    async def heartbeat(self):
        assert self._ws is not None
        await self._ws.send_bytes(packman.pack(heartbeat(), Operation.HEARTBEAT))
        self.logger.debug("heartbeat sended")

    async def listen(self):
        # start listening
        url, token = get_blive_ws_url(self.real_roomid)
        async with aiohttp.ClientSession().ws_connect(url) as ws:
            self._ws = ws
            await ws.send_bytes(
                packman.pack(certification(self.real_roomid, token), Operation.AUTH)
            )

            # 开始30s发送心跳包的定时任务
            self.scheduler.add_job(self.heartbeat, trigger="interval", seconds=30)
            self.scheduler.start()

            # 开始监听
            while True:
                msg: WSMessage = await ws.receive()
                if msg.type != aiohttp.WSMsgType.BINARY:
                    continue
                mq = packman.unpack(msg.data)
                self.logger.debug("received msg:\n{}", mq)
                tasks = [self.processor.process(BLiverCtx(self, m)) for m in mq]
                await asyncio.gather(*tasks)

    def run(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.listen())
        loop.run_forever()

    def run_as_task(self):
        loop = asyncio.get_event_loop()
        return loop.create_task(self.listen())
