import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, Redis

from config import TG_TOKEN
from handlers import game_router


async def main() -> None:
    bot = Bot(TG_TOKEN, parse_mode='HTML')
    redis = Redis(host='redis')
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)
    dp.include_router(game_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s: %(levelname)s] %(message)s')
    asyncio.run(main())
