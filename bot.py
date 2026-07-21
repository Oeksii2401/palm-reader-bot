import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from database import init_db, get_premium_notify_users
from utils import groq_ask
from prompts import DAILY_HOROSCOPE_PROMPT, DAILY_HOROSCOPE_FALLBACK_PROMPT
from astro import get_daily_personal_horoscope, format_astro_facts

from handlers import start, payments, readings, palmistry

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

KYIV_TZ = ZoneInfo("Europe/Kiev")
scheduler = AsyncIOScheduler(timezone=KYIV_TZ)


async def build_horoscope_text(row) -> str | None:
    """
    Пытается получить точный персональный гороскоп через FreeAstroAPI.
    Если API недоступен (сеть/лимиты/невалидные данные) — откатывается
    на старый упрощённый промпт по одной дате рождения, чтобы рассылка
    не сорвалась целиком из-за временного сбоя внешнего сервиса.
    """
    lang = row['lang'] or 'ru'
    if lang not in DAILY_HOROSCOPE_PROMPT:
        lang = 'ru'

    today_kyiv = datetime.now(KYIV_TZ)
    today_str  = today_kyiv.strftime("%d.%m.%Y")
    api_date   = today_kyiv.strftime("%Y-%m-%d")

    facts = None
    try:
        facts = await get_daily_personal_horoscope(
            year=row['birth_year'],
            month=row['birth_month'],
            day=row['birth_day'],
            hour=row['birth_hour'] or 12,
            minute=row['birth_minute'] or 0,
            city=row['birth_city'],
            date=api_date,
        )
    except Exception as e:
        logging.error(f"astro.get_daily_personal_horoscope failed for {row['user_id']}: {e}")

    if facts:
        sign = (facts.get("sign") or "").capitalize() or "—"
        facts_text = format_astro_facts(facts)
        prompt = DAILY_HOROSCOPE_PROMPT[lang].format(today=today_str, sign=sign, facts=facts_text)
        return await groq_ask(prompt)

    # ── Fallback: FreeAstroAPI недоступен — используем только дату рождения ──
    birth_date_str = f"{row['birth_day']:02d}.{row['birth_month']:02d}.{row['birth_year']}"
    prompt = DAILY_HOROSCOPE_FALLBACK_PROMPT[lang].format(today=today_str, birth_date=birth_date_str)
    return await groq_ask(prompt)


async def send_daily_horoscopes():
    now_time = datetime.now(KYIV_TZ).strftime("%H:%M")
    try:
        rows = await get_premium_notify_users(now_time)
        for row in rows:
            try:
                result = await build_horoscope_text(row)
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
