from blive import BLiver, Events, BLiverCtx
from blive.msg import DanMuMsg, HotRankChangeV2Msg, InteractWordMsg, SendGiftMsg

app = BLiver(22820500)


@app.on(Events.DANMU_MSG)
async def listen(ctx: BLiverCtx):
    danmu = DanMuMsg(ctx.body)
    print(
        f"\n{danmu.sender['name']}({danmu.sender['medal']['medal_name']}:{danmu.sender['medal']['medal_level']}): \"{danmu.content}\"\n "
    )


@app.on(Events.INTERACT_WORD)
async def listen_join(ctx: BLiverCtx):
    join = InteractWordMsg(ctx.body)
    print(
        "欢迎",
        f"{join.user['name']} ({join.user['medal']['medal_name']}:{join.user['medal']['medal_level']})",
        "进入直播间",
    )


@app.on(Events.SUPER_CHAT_MESSAGE)
async def listen_sc(ctx: BLiverCtx):
    print(ctx.body)


@app.on(Events.SEND_GIFT)
async def listen_gift(ctx: BLiverCtx):
    msg = SendGiftMsg(ctx.body)
    print(f"{msg.sender['name']} 送出 {msg.gift['gift_name']}")


@app.on(Events.HOT_RANK_CHANGED_V2)
async def hot(ctx: BLiverCtx):
    msg = HotRankChangeV2Msg(ctx.body)
    print(
        f"恭喜 {ctx.bliver.uname} 在 {msg.area_name} 区 的 {msg.rank_desc} 榜单中获得第 {msg.rank} 名"
    )


app.run()
