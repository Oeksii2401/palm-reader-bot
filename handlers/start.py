import logging
from datetime import datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_IDS, FREE_LIMIT, REF_DAYS_L1, REF_DAYS_L2, AARON_PHOTO_URL
from database import db_pool, get_or_create_user, save_lang
from texts import TEXTS
from keyboards import lang_kb, menu_kb, back_kb
from state import user_state, get_state

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    uid  = message.from_user.id
    args = message.text.split()

    await get_or_create_user(uid)

    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        async with db_pool.acquire() as conn:
            referrer = await conn.fetchrow(
                "SELECT user_id FROM users WHERE ref_code=$1", ref_code
            )
            if referrer and referrer['user_id'] != uid:
                await conn.execute(
                    "UPDATE users SET referred_by=$1 WHERE user_id=$2 AND referred_by IS NULL",
                    referrer['user_id'], uid
                )

    user_state[uid] = {"step": "lang"}

    try:
        await message.answer_photo(
            photo=AARON_PHOTO_URL,
            caption="🔮 Вітаю / Привет / Hello / Hallo!\n\n<b>Aaron — Palmist & Astrologer</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await message.answer(
        "🔮 Вітаю / Привет / Hello / Hallo!",
        reply_markup=lang_kb()
    )


@router.message(Command("notify"))
async def cmd_notify(message: Message):
    uid   = message.from_user.id
    state = get_state(uid)
    lang  = state.get("lang", "ru")
    t     = TEXTS[lang]
    user  = await get_or_create_user(uid)
    now   = datetime.now()

    is_premium = (
        user['is_subscribed'] and user['sub_until'] and
        user['sub_until'] > now and (user['plan'] or 0) == 2
    )
    if uid not in ADMIN_IDS and not is_premium:
        await message.answer(t["notify_no_premium"])
        return

    state.update({"step": "notify_date"})
    await message.answer(t["notify_ask_date"], reply_markup=back_kb(lang))


@router.message(Command("ref"))
async def cmd_ref(message: Message):
    uid   = message.from_user.id
    state = get_state(uid)
    lang  = state.get("lang", "ru")
    t     = TEXTS[lang]
    user  = await get_or_create_user(uid)
    bot   = message.bot
    info  = await bot.get_me()
    link  = f"https://t.me/{info.username}?start=ref_{user['ref_code']}"
    await message.answer(
        t["ref_link_msg"].format(link=link, l1=REF_DAYS_L1, l2=REF_DAYS_L2),
        parse_mode="HTML"
    )


@router.message(Command("sub"))
async def cmd_sub(message: Message):
    uid   = message.from_user.id
    state = get_state(uid)
    lang  = state.get("lang", "ru")
    t     = TEXTS[lang]
    user  = await get_or_create_user(uid)
    now   = datetime.now()

    if user['is_subscribed'] and user['sub_until'] and user['sub_until'] > now:
        plan_name = t['plan_premium'] if (user['plan'] or 0) == 2 else t['plan_standard']
        status    = t['sub_active'].format(plan=plan_name, date=user['sub_until'].strftime("%d.%m.%Y"))
    elif user['is_subscribed']:
        status = t['sub_expired']
    else:
        status = t['sub_free'].format(used=user['free_uses'] or 0, limit=FREE_LIMIT)

    info = await message.bot.get_me()
    link = f"https://t.me/{info.username}?start=ref_{user['ref_code']}"
    await message.answer(t["sub_info"].format(status=status, link=link), parse_mode="HTML")
