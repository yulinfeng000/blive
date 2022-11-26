import json
import asyncio
from typing import List, Union
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from requests.exceptions import ConnectionError
from pyee import AsyncIOEventEmitter
from .core import (
    BLiveMsgPackage,
    PackageHeader,
    Events,
    Operation,
    get_blive_room_info,
    get_blive_ws_url,
    certification,
    heartbeat,
)


class BLiverCtx:
    def __init__(self, bliver, msg) -> None:
        self.ws = bliver.ws
        self.bliver: BLiver = bliver
        self.msg:tuple[PackageHeader,dict] = msg  # 原始消息
        self.header: PackageHeader = self.msg[0]  # 消息头部
        self.body:dict = json.loads(msg[1])

class BLiver(AsyncIOEventEmitter):
    def __init__(self, room_id, uid=0):
        super().__init__()
        self.running = False
        self.ws = None
        self.room_id = room_id
        self.uid = uid
        self.real_room_id, self.uname = get_blive_room_info(room_id)
        self.packman = BLiveMsgPackage()
        self.scheduler = AsyncIOScheduler(timezone="Asia/ShangHai")
        self.aio_session = aiohttp.ClientSession()

    def register_handler(self, event: Union[Events, List[Events]], handler):
        self.on(event, handler)

    async def heartbeat(self):
        try:
            if self.ws is not None and not self.ws.closed:
                await self.ws.send_bytes(
                    self.packman.pack(heartbeat(), Operation.HEARTBEAT)
                )
                return
        except (
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
            ConnectionError,
            ConnectionResetError,
        ):
            await self.connect()  # 重新连接

    async def connect(self, retries=5):
        for _ in range(retries):
            try:
                url, token = get_blive_ws_url(self.real_room_id)
                self.ws = await self.aio_session.ws_connect(url)
                # 发送认证
                await self.ws.send_bytes(
                    self.packman.pack(
                        certification(self.real_room_id, token, uid=self.uid),
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
                await asyncio.sleep(1)
        raise aiohttp.ClientConnectionError("与服务器连接失败")
    
    async def listen(self):
        self.running = True
        # start listening
        await self.connect()

        # 开始30s发送心跳包的定时任务
        self.scheduler.add_job(self.heartbeat, trigger="interval", seconds=30)
        self.scheduler.start()

        # 开始监听
        while self.running:
            try:
                msg = await self.ws.receive(timeout=60)
                if msg.type in (
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    if self.running:
                        await self.connect()  # reconnect
                        continue
                if msg.type != aiohttp.WSMsgType.BINARY:
                    continue
                mq = self.packman.unpack(msg.data)
                ctxs = [BLiverCtx(self, m) for m in mq]
                ctxs = filter(lambda ctx:ctx.body.get("cmd",None), ctxs)
                for ctx in ctxs:
                    self.emit(ctx.body["cmd"],ctx)
            except (
                aiohttp.ClientConnectionError,
                ConnectionResetError,
                asyncio.TimeoutError,
            ):
                await self.connect()

    async def graceful_close(self):
        self.running = False
        self.scheduler.shutdown()
        await self.aio_session.close()
        await self.ws.close()
        

    def run(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.listen())
        loop.run_forever()

    def run_as_task(self):
        loop = asyncio.get_event_loop()
        return loop.create_task(self.listen())