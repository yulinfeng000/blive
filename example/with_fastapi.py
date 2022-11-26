import uvicorn
from fastapi import FastAPI
from blive import BLiver, Events
from blive.msg import DanMuMsg

app = FastAPI()

BLIVER_POOL = {}


def create_bliver(roomid):
    # 定义弹幕事件handler
    async def listen(ctx):
        danmu = DanMuMsg(ctx.body)
        print(
            f'\n{danmu.sender.name} ({danmu.sender.medal.medal_name}:{danmu.sender.medal.medal_level}): "{danmu.content}"\n'
        )

    b = BLiver(roomid)
    b.register_handler(Events.DANMU_MSG, listen)
    return b


@app.get("/create")
async def create_new_bliver(roomid: int):
    room = BLIVER_POOL.get(roomid, None)
    if not room:
        b = create_bliver(roomid)
        BLIVER_POOL[roomid] = b.run_as_task()
    return {"msg": "创建一个新直播间弹幕监听成功"}


@app.get("/del")
async def rm_bliver(roomid: int):
    room = BLIVER_POOL.get(roomid, None)
    if room:
        room.cancel()
        BLIVER_POOL.pop(roomid)
    return {"msg": "移除直播间弹幕监听成功"}


@app.get("/show")
async def show():
    return list(BLIVER_POOL.keys())


if __name__ == "__main__":
    uvicorn.run(app)