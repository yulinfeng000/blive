"""监听多个直播间的例子"""

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
