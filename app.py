from blive import BLiver, Events, BLiverCtx, DanMuMsg

app = BLiver(510)


@app.handler(Events.DANMU_MSG)
async def listen(ctx: BLiverCtx):
    danmu = DanMuMsg(ctx.body)
    print(danmu.content())
    print(danmu.sender())
    print(danmu.timestamp())


app.run()
