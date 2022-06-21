"""监听多个直播间的例子"""

import asyncio
from blive import BLiver, Events, BLiverCtx
from blive.msg import DanMuMsg

# 多个对象共用的全局异常处理
# 首先定义全局异常处理handler


def global_error_handler(e, app: BLiver):
    print(f"{app.uname} 全局异常捕获", e)


# 调用类方法注册异常以及其处理函数,需在实例化之前注册，注册后所有BLiver共同拥有该异常处理
BLiver.register_global_error_handler(ZeroDivisionError, global_error_handler)


# 定义弹幕事件handler,为了演示异常处理直接在方法中抛出异常
async def azi_timeout_error(ctx: BLiverCtx):
    raise TimeoutError


async def ke_type_error(ctx):
    raise TypeError


async def zero_division_error(ctx):
    1 / 0


# 两个直播间
ke = BLiver(21716679)
azi = BLiver(7983476)

# 注册handler
ke.register_handler(Events.INTERACT_WORD, zero_division_error)
azi.register_handler(Events.INTERACT_WORD, zero_division_error)
ke.register_handler(Events.DANMU_MSG, ke_type_error)
azi.register_handler(Events.DANMU_MSG, azi_timeout_error)


# 类实例级别的异常处理，实例与实例之间不共享
ke.register_error_handler(
    TypeError, lambda e, app: print(f"{app.uname} catch TypeError", e)
)

# 实例级别的异常处理可以用注解方式进行注册
@azi.catch(TimeoutError)
def azi_handler(e, app):
    print(f"{app.uname} catch TimeoutError", e)


async def main():

    # 以异步task的形式运行
    task1 = ke.run_as_task()
    task2 = azi.run_as_task()

    # await 两个任务
    await asyncio.gather(*[task1, task2])


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
