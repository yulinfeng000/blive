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

## 项目简介

- blive 文件夹为框架代码
- app.py 为一个简单示例

## TODO

- 打包发布
- 更多的消息操作类
- 尝试加入中间件架构
