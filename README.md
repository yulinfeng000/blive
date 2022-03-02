# B 站弹幕监听框架

## 特点

- 简单，只需房间号即可监听
- 异步，io 不阻塞，及时获取消息

## B 站直播弹幕 websocket 协议分析

[PROTOCOL 分析](./PROTOCOL.md)

## 快速开始

1. 安装

   `pip install blive`

2. 创建 app

   ```python
   from blive import  BLiver

   app = BLiver(123) #123为房间号
   ```

3. 创建处理器

   ```python
   from blive import  BLiver, Events, BLiverCtx

   app = BLiver(123)

   # 标记该方法监听弹幕消息,更多消息类型请参考 Events 类源代码
   @app.on(Events.DANMU_MSG)
   async def listen_danmu(ctx: BLiverCtx):
       danmu = DanMuMsg(ctx.body) #ctx.body 套上相应的消息操作类即可得到消息的基本内容,也可直接操作 ctx.body
       print(danmu.content)
       print(danmu.sender)
       print(danmu.timestamp)
   ```

4. 运行

   ```python

   from blive import  BLiver, Events, BLiverCtx

   app = BLiver(123)

   @app.on(Events.DANMU_MSG)
   async def listen_danmu(ctx: BLiverCtx):
       danmu = DanMuMsg(ctx.body)
       print(danmu.content)
       print(danmu.sender)
       print(danmu.timestamp)

   app.run() # 运行app!

   ```

## 同时监听多个直播间

```python
import asyncio
from blive import BLiver, Events, BLiverCtx
from blive.msg import DanMuMsg


# 定义弹幕事件handler
async def listen(ctx: BLiverCtx):
   danmu = DanMuMsg(ctx.body)
   print(
      f'\n{danmu.sender.name} ({danmu.sender.medal.medal_name}:{danmu.sender.medal.medal_level}): "{danmu.content}"\n'
   )


async def main():
   # 两个直播间
   ke = BLiver(605)
   azi = BLiver(510)

   # 注册handler
   ke.register_handler(Events.DANMU_MSG, listen)
   azi.register_handler(Events.DANMU_MSG, listen)

   # 以异步task的形式运行
   task1 = ke.run_as_task()
   task2 = azi.run_as_task()

   # await 两个任务
   await asyncio.gather(*[task1, task2])


if __name__ == "__main__":
   loop = asyncio.get_event_loop()
   loop.run_until_complete(main()) 
```

## 作为协议解析工具在其他地方使用（伪代码）

```python
from blive.core import BWS_MsgPackage

packman = BWS_MsgPackage() # 实例化一个消息包处理器

while True:
   data = ws.receive() # 当收到消息时
   msg = packman.unpack(data) # 使用packman解析消息,返回一个形如 [(header,body), (header,body), ... ] 数组
   # 如果你想发送弹幕之类的消息，可以自行构建消息数据并使用packman.pack方法打包消息
   print(msg)
```

## 项目简介

- blive 文件夹为框架代码

  - core.py 为B站ws直播聊天室协议包处理的核心代码

  - framework.py 为框架代码

  - msg.py 为消息操作类代码

- app.py , multi_room.py 为2个简单示例，分别是以框架运行和同时监听多个直播间的实现

## TODO

- 更多的消息操作类（欢迎各位提pr）
- 尝试加入中间件架构（目前感觉需求不大）
