import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import start, upload, analytics, settings, content, vk, avito
from database.requests import create_tables
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

async def main():
    await create_tables()
    print("Таблицы созданы!")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(upload.router)
    dp.include_router(analytics.router)
    dp.include_router(settings.router)
    dp.include_router(content.router)
    dp.include_router(vk.router)
    dp.include_router(avito.router)

    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
