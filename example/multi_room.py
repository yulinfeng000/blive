"""监听多个直播间的例子"""

import asyncio
from blive import BLiver, Events, BLiverCtx
from blive.msg import DanMuMsg,InteractWordMsg


# 定义弹幕事件handler
async def listen(ctx: BLiverCtx):
    danmu = DanMuMsg(ctx.body)
    print(
        f'\n【{ctx.bliver.uname}】{danmu.sender.name} ({danmu.sender.medal.medal_name}:{danmu.sender.medal.medal_level}): "{danmu.content}"\n'
    )

async def listen_join(ctx: BLiverCtx):
    join = InteractWordMsg(ctx.body)
    print(
        f"\n【{ctx.bliver.uname}】欢迎",
        f"{join.user['name']} ({join.user['medal']['medal_name']}:{join.user['medal']['medal_level']})",
        "进入直播间",
    )

async def main():
    # 两个直播间
    hai7 = BLiver(7777)
    azi = BLiver(510)

    azi.on(Events.DANMU_MSG, listen)
    azi.on(Events.INTERACT_WORD, listen_join)
        # 注册handler
    hai7.on(Events.DANMU_MSG, listen)
    hai7.on(Events.INTERACT_WORD, listen_join)

    # 以异步task的形式运行
    task1 = hai7.run_as_task()
    task2 = azi.run_as_task()

    # await 两个任务
    await asyncio.gather(task1, task2)


if __name__ == "__main__":
    asyncio.run(main())
