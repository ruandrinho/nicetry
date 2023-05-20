import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from config import TG_TOKEN
from handlers import game_router, redis


async def main() -> None:
    bot = Bot(TG_TOKEN, parse_mode='HTML')
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)
    dp.include_router(game_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
