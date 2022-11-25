import sys
import json
import asyncio
from typing import Awaitable, Dict, List, Union
import loguru
import aiohttp
from aiohttp.client_ws import ClientWebSocketResponse
from aiohttp.http_websocket import WSMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.util import _Undefined
from requests.exceptions import ConnectionError

from .core import (
    BWS_MsgPackage,
    PackageHeader,
    Events,
    Operation,
    get_blive_room_info,
    get_blive_ws_url,
    certification,
    heartbeat,
)


undefined = _Undefined()


class ExitedException(Exception):
    pass


class BLiverCtx(object):
    def __init__(self, bliver, msg) -> None:
        super().__init__()
        self.ws: ClientWebSocketResponse = bliver.ws
        self.msg = msg  # 原始消息
        self.header: PackageHeader = msg[0]  # 消息头部
        self.bliver: BLiver = bliver
        self.body = json.loads(msg[1])


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

    def register(self, channel: str, handler: Awaitable):
        c = self.channels.get(channel, Channel())
        c.register_handler(handler)
        self.channels[channel] = c

    async def process(self, ctx):
        if ctx.header.operation == Operation.NOTIFY:
            listeners = self.channels.get(ctx.body["cmd"], [])  # 根据cmd 得到相应的处理句柄
            return await asyncio.gather(*[f(ctx) for f in listeners])


class BLiver:
    _global_catches = {}

    def catch(self, err_type):
        def _err_handler_wrapper(fn):
            self.register_error_handler(err_type, fn)

        return _err_handler_wrapper

    @classmethod
    def register_global_error_handler(cls, err_type, fn):
        err_handlers = cls._global_catches.get(err_type, [])
        err_handlers.append(fn)
        cls._global_catches[err_type] = err_handlers

    def register_error_handler(self, err_type, fn):
        err_handlers = self._catches.get(err_type, [])
        err_handlers.append(fn)
        self._catches[err_type] = err_handlers

    def __init__(self, roomid, uid=0, logger=None, log_level="INFO"):
        self.roomid = roomid
        self.uid = uid
        self.real_roomid, self.uname = get_blive_room_info(roomid)
        if not logger:
            self.logger = loguru.logger
            self.logger.remove()
            self.logger.add(sys.stderr, level=log_level)
        else:
            self.logger = logger
        self._catches = {}  # to handle errors
        self._ws: ClientWebSocketResponse = None
        self.packman = BWS_MsgPackage()
        self.scheduler = AsyncIOScheduler(timezone="Asia/ShangHai")
        self.processor = Processor(logger=self.logger)
        self.aio_session = aiohttp.ClientSession()

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
        try:
            if self._ws is not None and not self._ws.closed:
                await self._ws.send_bytes(
                    self.packman.pack(heartbeat(), Operation.HEARTBEAT)
                )
                self.logger.debug("heartbeat sended")
                return
            else:
                self.logger.warning(
                    "heartbeat msg not send successfully, because ws had closed"
                )
        except (
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
            ConnectionError,
            ConnectionResetError,
        ):
            self.logger.warning("send heartbeat error, will reconnect ws")
            await self.connect()  # 重新连接

    async def connect(self, retries=5):
        for i in range(retries):
            try:
                url, token = get_blive_ws_url(self.real_roomid)
                ws = await self.aio_session.ws_connect(url)
                self._ws = ws
                # 发送认证
                await ws.send_bytes(
                    self.packman.pack(
                        certification(self.real_roomid, token, uid=self.uid),
                        Operation.AUTH,
                    )
                )
                return
            except (
                aiohttp.ClientConnectionError,
                asyncio.TimeoutError,
                ConnectionError,
                ConnectionResetError,
            ):
                self.logger.warning(
                    "connect failed, will retry {}, current: {}", retries, i + 1
                )
                await asyncio.sleep(1)
        self.logger.warning("reconnect fail")

    async def listen(self):
        # start listening
        await self.connect()

        # 开始30s发送心跳包的定时任务
        self.scheduler.add_job(self.heartbeat, trigger="interval", seconds=30)
        self.scheduler.start()

        # 开始监听
        while True:
            try:
                msg: WSMessage = await self.ws.receive(timeout=60)
                if msg.type in (
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    self.logger.warning("ws closed")
                    await self.connect()  # reconnect
                    continue
                if msg.type != aiohttp.WSMsgType.BINARY:
                    continue
                mq = self.packman.unpack(msg.data)
                self.logger.debug("received msg:\n{}", mq)
                tasks = [self.processor.process(BLiverCtx(self, m)) for m in mq]
                await asyncio.gather(*tasks)
            except (
                aiohttp.ClientConnectionError,
                ConnectionResetError,
                asyncio.TimeoutError,
            ):
                self.logger.warning("ws conn will reconnect")
                await self.connect()

            # to handler errors
            except tuple(self._catches.keys()) as e:
                [eh(e,self) for eh in self._catches.get(type(e), [])]
            except tuple(BLiver._global_catches.keys()) as e:
                [eh(e,self) for eh in BLiver._global_catches.get(type(e), [])]

    async def graceful_close(self):
        await self._ws.close()
        await self.aio_session.close()
        self.scheduler.shutdown()
        self.running = False

    def run(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.listen())
        loop.run_forever()

    def run_as_task(self):
        loop = asyncio.get_event_loop()
        return loop.create_task(self.listen())
