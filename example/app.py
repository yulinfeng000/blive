from blive import BLiver,  Events, BLiverCtx
from blive.msg import (
    DanMuMsg,
    EntryEffectMsg,
    HotRankChangeV2Msg,
    InteractWordMsg,
    OnlineRankCountMsg,
    SendGiftMsg,
    StopLiveRoomListMsg,
    SuperChatMsg,
)

app = BLiver(510)


@app.on(Events.DANMU_MSG)
async def listen(ctx: BLiverCtx):
    danmu = DanMuMsg(ctx.body)
    print(
        f'[弹幕] {danmu.sender.name} ({danmu.sender.medal.medal_name}:{danmu.sender.medal.medal_level}): "{danmu.content}"\n'
    )


@app.on(Events.INTERACT_WORD)
async def listen_join(ctx: BLiverCtx):
    join = InteractWordMsg(ctx.body)
    print(
        "[欢迎]",
        f"{join.user['name']} ({join.user['medal']['medal_name']}:{join.user['medal']['medal_level']})",
        "进入直播间\n",
    )


@app.on(Events.SUPER_CHAT_MESSAGE)
async def listen_sc(ctx: BLiverCtx):
    msg = SuperChatMsg(ctx.body)
    print(
        f"[sc] 感谢 {msg.sender['name']}({msg.sender['medal']['medal_name']}:{msg.sender['medal']['medal_level']})的价值 {msg.price} 的sc\n\n\t{msg.content}\n"
    )


@app.on(Events.SEND_GIFT)
async def listen_gift(ctx: BLiverCtx):
    msg = SendGiftMsg(ctx.body)
    print(
        f"[礼物] {msg.sender['name']} ({msg.sender['medal']['medal_name']}:{msg.sender['medal']['medal_level']}) 送出 {msg.gift['gift_name']}\n"
    )


@app.on(Events.HOT_RANK_CHANGED_V2)
async def hot(ctx: BLiverCtx):
    msg = HotRankChangeV2Msg(ctx.body)
    print(
        f"[通知] 恭喜 {ctx.bliver.uname} 在 {msg.area_name} 区 的 {msg.rank_desc} 榜单中获得第 {msg.rank} 名\n"
    )


@app.on(Events.ENTRY_EFFECT)
async def welcome_captain(ctx: BLiverCtx):
    msg = EntryEffectMsg(ctx.body)
    print(f"[热烈欢迎] {msg.copy_writting}\n")


@app.on(Events.STOP_LIVE_ROOM_LIST)
async def stop_live_room_list(ctx: BLiverCtx):
    # 监听停止直播的房间
    msg = StopLiveRoomListMsg(ctx.body)
    print(f"[通知] 停止直播的房间列表:{msg.room_id_list}\n")


@app.on(Events.ONLINE_RANK_COUNT)
async def online_rank(ctx):
    msg = OnlineRankCountMsg(ctx.body)
    print(f"[通知] 当前在线人气排名 {msg.count}\n")


app.run()
