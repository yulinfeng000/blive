import sys
import json
import asyncio
from typing import Dict, Tuple
import aiohttp
from aiohttp.client_ws import ClientWebSocketResponse
from aiohttp.http_websocket import WSMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import loguru
from apscheduler.util import _Undefined
from .core import (
    Events,
    Operation,
    PackageHeader,
    packman,
    get_blive_room_id,
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


class Processor:
    def __init__(self, logger=None) -> None:
        self.logger = logger or loguru.logger
        self.channels = {}
        for e in Events:
            self.channels[e] = []

    def register(self, channel, handler):
        handlers = self.channels.get(channel, None)
        handlers.append(handler)

    async def process(self, ctx):
        header: PackageHeader = ctx.msg[0]
        msg = json.loads(ctx.msg[1])
        ctx.body = msg
        if header.operation == Operation.NOTIFY:
            handlers = self.channels.get(msg["cmd"], [])  # 根据cmd 得到相应的处理句柄
            await asyncio.gather(*[c(ctx) for c in handlers])


class BLiver:
    def __init__(self, roomid, logger=None, log_level="INFO"):
        self.roomid = roomid
        if not logger:
            self.logger = loguru.logger
            self.logger.remove()
        else:
            self.logger = logger
        self.logger.add(sys.stderr, level=log_level)
        self._ws: ClientWebSocketResponse = None
        self.scheduler = AsyncIOScheduler(timezone="Asia/ShangHai")
        self.processor = Processor(logger=self.logger)

    def handler(self, event: Events):
        def f_wrapper(func):
            self.logger.debug("handler added")
            self.processor.register(event, func)
            return func

        return f_wrapper

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
        assert self._ws
        return self._ws

    async def heartbeat(self):
        assert self._ws
        await self._ws.send_bytes(packman.pack(heartbeat(), Operation.HEARTBEAT))
        self.logger.debug("heartbeat sended")

    async def listen(self):
        rommid, _, _ = get_blive_room_id(self.roomid)  # 如果是短id,就得到直播间真实id
        url, token = get_blive_ws_url(rommid)
        async with aiohttp.ClientSession().ws_connect(url) as ws:
            self._ws = ws
            await ws.send_bytes(
                packman.pack(certification(rommid, token), Operation.AUTH)
            )
            self.scheduler.add_job(self.heartbeat, trigger="interval", seconds=30)
            self.scheduler.start()
            # 开始监听
            while True:
                msg: WSMessage = await ws.receive()
                # print(msg)
                if msg.type != aiohttp.WSMsgType.BINARY:
                    continue
                # print(msg.data)
                mq = packman.unpack(msg.data)
                self.logger.debug("received msg:\n{}", mq)
                tasks = [self.processor.process(BLiverCtx(self, m)) for m in mq]
                await asyncio.gather(*tasks)

    def run(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.listen())
        loop.run_forever()
