# main.py
import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
import os

from app.database import init_db, close_db, load_tests_from_dict
from tests_database import tests_database

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    await init_db()
    
    await load_tests_from_dict(tests_database)
    
    from app.handlers import start, stats, exam
    
    dp.include_router(start.router)
    dp.include_router(stats.router)
    dp.include_router(exam.router)
    
    print("Бот запущен...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен")
    finally:
        asyncio.run(close_db())