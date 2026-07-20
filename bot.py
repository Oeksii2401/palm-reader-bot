import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from database import init_db, get_premium_notify_users
from utils import groq_ask
from prompts import DAILY_HOROSCOPE_PROMPT

from handlers import start, payments, readings, palmistry

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

KYIV_TZ = ZoneInfo("Europe/Kiev")
scheduler = AsyncIOScheduler(timezone=KYIV_TZ)


async def send_daily_horoscopes():
    now_kyiv = datetime.now(KYIV_TZ)
    now_time = now_kyiv.strftime("%H:%M")
    today    = now_kyiv.strftime("%d.%m.%Y")
    try:
        rows = await get_premium_notify_users(now_time)
        for row in rows:
            try:
                lang       = row['lang'] or 'ru'
                birth_date = row['birth_date']
                prompt     = DAILY_HOROSCOPE_PROMPT[lang].format(today=today, birth_date=birth_date)
                result     = await groq_ask(prompt)
                await bot.send_message(
                    row['user_id'],
                    f"🌅 *Ваш гороскоп на сегодня:*\n\n{result}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Daily horoscope error for {row['user_id']}: {e}")
    except Exception as e:
        logging.error(f"Scheduler DB error: {e}")


async def main():
    await init_db()

    dp.include_router(start.router)
    dp.include_router(payments.router)
    dp.include_router(palmistry.router)
    dp.include_router(readings.router)

    scheduler.add_job(send_daily_horoscopes, "cron", minute="*")
    scheduler.start()

    print("🔮 Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
