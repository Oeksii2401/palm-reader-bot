import re
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, LabeledPrice

from config import ADMIN_IDS, STANDARD_STARS, PREMIUM_STARS
from database import get_or_create_user, save_lang, can_use, increment_uses
from texts import TEXTS
from keyboards import (
    lang_kb, menu_kb, hand_kb, back_kb, paywall_kb,
    ALL_STANDARD_BTNS, ALL_PREMIUM_BTNS
)
from prompts import (
    NUMEROLOGY_PROMPT, NATAL_PROMPT, COMPAT_PROMPT, HOROSCOPE_PROMPT,
    NAME_PROMPT_FREE, NAME_PROMPT_STANDARD, NAME_PROMPT_PREMIUM
)
from utils import send_long, send_loading_gif, groq_ask
from state import user_state, get_state

router = Router()




async def check_access(message: Message, uid: int, lang: str) -> bool:
    if await can_use(uid):
        return True
    t = TEXTS[lang]
    user_state[uid] = {**user_state.get(uid, {}), "step": "paywall", "lang": lang}
    await message.answer(t["paywall"], reply_markup=paywall_kb(lang), parse_mode="HTML")
    return False


async def send_sub_invoice(uid: int, plan: str, lang: str, bot):
    t = TEXTS[lang]
    if plan == "standard":
        await bot.send_invoice(
            chat_id=uid,
            title=t["inv_standard_title"],
            description=t["inv_standard_desc"],
            payload="standard",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=t["inv_standard_title"], amount=STANDARD_STARS)],
        )
    else:
        await bot.send_invoice(
            chat_id=uid,
            title=t["inv_premium_title"],
            description=t["inv_premium_desc"],
            payload="premium",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=t["inv_premium_title"], amount=PREMIUM_STARS)],
        )


def get_name_prompt(user: dict, lang: str, uid: int) -> str:
    """Выбирает промпт в зависимости от уровня подписки."""
    now = datetime.now()
    is_admin = uid in ADMIN_IDS
    is_premium = (
        user['is_subscribed'] and user['sub_until'] and
        user['sub_until'] > now and (user['plan'] or 0) == 2
    )
    is_standard = (
        user['is_subscribed'] and user['sub_until'] and
        user['sub_until'] > now and (user['plan'] or 0) >= 1
    )
    if is_admin or is_premium:
        return NAME_PROMPT_PREMIUM[lang]
    elif is_standard:
        return NAME_PROMPT_STANDARD[lang]
    else:
        return NAME_PROMPT_FREE[lang]


def get_name_hint(user: dict, lang: str, uid: int) -> str | None:
    """Возвращает подсказку об апгрейде или None если уже максимум."""
    now = datetime.now()
    if uid in ADMIN_IDS:
        return None
    is_premium = (
        user['is_subscribed'] and user['sub_until'] and
        user['sub_until'] > now and (user['plan'] or 0) == 2
    )
    is_standard = (
        user['is_subscribed'] and user['sub_until'] and
        user['sub_until'] > now and (user['plan'] or 0) >= 1
    )
    t = TEXTS[lang]
    if is_premium:
        return None
    elif is_standard:
        return t["name_upgrade_prem"]
    else:
        return t["name_upgrade_std"]


@router.message(F.text)
async def handle_text(message: Message):
    uid   = message.from_user.id
    text  = message.text.strip()
    state = get_state(uid)
    step  = state.get("step", "lang")
    lang  = state.get("lang", "ru")
    t     = TEXTS.get(lang, TEXTS["ru"])

    # ── Глобальный перехват кнопок подписки ─
    if text in ALL_STANDARD_BTNS:
        await send_sub_invoice(uid, "standard", lang, message.bot)
        return
    if text in ALL_PREMIUM_BTNS:
        await send_sub_invoice(uid, "premium", lang, message.bot)
        return

    # ── Выбор языка ─────────────────────────
    if step == "lang":
        lang_map = {
            "🇺🇦 Українська": "uk",
            "🇷🇺 Русский":    "ru",
            "🇬🇧 English":    "en",
            "🇩🇪 Deutsch":    "de",
        }
        if text in lang_map:
            lang = lang_map[text]
            await get_or_create_user(uid)
            await save_lang(uid, lang)
            user_state[uid] = {"lang": lang, "step": "menu"}
            await message.answer(TEXTS[lang]["choose_menu"], reply_markup=menu_kb(lang))
        else:
            await message.answer("🔮", reply_markup=lang_kb())
        return

    # ── Выход ───────────────────────────────
    if text == t.get("exit_btn"):
        user_state[uid] = {"step": "lang"}
        await message.answer(t["exit_msg"], reply_markup=ReplyKeyboardRemove())
        return

    # ── Назад в меню ────────────────────────
    if text == t["back"]:
        user_state[uid] = {"lang": lang, "step": "menu"}
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── Главное меню ────────────────────────
    if step == "menu":
        if text == t["menu_palm"]:
            if not await check_access(message, uid, lang):
                return
            user_state[uid].update({"step": "palm_hand"})
            await message.answer(t["choose_hand"], reply_markup=hand_kb(lang))
        elif text == t["menu_num"]:
            if not await check_access(message, uid, lang):
                return
            user_state[uid].update({"step": "num_input"})
            await message.answer(t["num_ask"], reply_markup=back_kb(lang))
        elif text == t["menu_natal"]:
            if not await check_access(message, uid, lang):
                return
            user_state[uid].update({"step": "natal_input"})
            await message.answer(t["natal_ask"], reply_markup=back_kb(lang))
        elif text == t["menu_compat"]:
            if not await check_access(message, uid, lang):
                return
            user_state[uid].update({"step": "compat_1"})
            await message.answer(t["compat_ask1"], reply_markup=back_kb(lang))
        elif text == t["menu_horoscope"]:
            if not await check_access(message, uid, lang):
                return
            user_state[uid].update({"step": "horoscope_input"})
            await message.answer(t["horoscope_ask"], reply_markup=back_kb(lang))
        elif text == t["menu_name"]:
            if not await check_access(message, uid, lang):
                return
            user_state[uid].update({"step": "name_input"})
            await message.answer(t["name_ask"], reply_markup=back_kb(lang))
        else:
            await message.answer(t["unexpected"], reply_markup=menu_kb(lang))
        return

    # ── Хиромантия — выбор руки ─────────────
    if step == "palm_hand":
        if text == t["left_btn"]:
            user_state[uid].update({"step": "palm_photo", "hand": "left"})
            await message.answer(t["send_left"], reply_markup=back_kb(lang))
        elif text == t["right_btn"]:
            user_state[uid].update({"step": "palm_photo", "hand": "right"})
            await message.answer(t["send_right"], reply_markup=back_kb(lang))
        elif text == t["both_btn"]:
            user_state[uid].update({"step": "palm_left", "hand": "both"})
            await message.answer(t["send_left"], reply_markup=back_kb(lang))
        else:
            await message.answer(t["choose_hand"], reply_markup=hand_kb(lang))
        return

    # ── Нумерология ──────────────────────────
    if step == "num_input":
        gif_msg = await send_loading_gif(message, t["num_analyzing"])
        try:
            current_date = datetime.now().strftime("%d.%m.%Y")
            prompt = NUMEROLOGY_PROMPT[lang].format(date=current_date) + text
            result = await groq_ask(prompt)
            try:
                await gif_msg.delete()
            except Exception:
                pass
            await send_long(message, result)
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── Натальная карта ───────────────────────
    if step == "natal_input":
        gif_msg = await send_loading_gif(message, t["natal_analyzing"])
        try:
            current_date = datetime.now().strftime("%d.%m.%Y")
            prompt = NATAL_PROMPT[lang].format(date=current_date) + text
            result = await groq_ask(prompt)
            try:
                await gif_msg.delete()
            except Exception:
                pass
            await send_long(message, result)
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── Совместимость ────────────────────────
    if step == "compat_1":
        user_state[uid].update({"step": "compat_2", "compat_1": text})
        await message.answer(t["compat_ask2"])
        return

    if step == "compat_2":
        person1 = state.get("compat_1", "")
        gif_msg = await send_loading_gif(message, t["compat_analyzing"])
        try:
            current_date = datetime.now().strftime("%d.%m.%Y")
            prompt = (
                COMPAT_PROMPT[lang].format(date=current_date) +
                f"Людина 1 / Человек 1 / Person 1: {person1} | "
                f"Людина 2 / Человек 2 / Person 2: {text}"
            )
            result = await groq_ask(prompt)
            try:
                await gif_msg.delete()
            except Exception:
                pass
            await send_long(message, result)
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── Гороскоп ──────────────────────────────
    if step == "horoscope_input":
        today    = datetime.now().strftime("%d.%m.%Y")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
        gif_msg  = await send_loading_gif(message, t["horoscope_calc"])
        try:
            prompt = HOROSCOPE_PROMPT[lang].format(today=today, tomorrow=tomorrow) + text
            result = await groq_ask(prompt)
            try:
                await gif_msg.delete()
            except Exception:
                pass
            await send_long(message, result)
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── Толкование имени ─────────────────────
    if step == "name_input":
        gif_msg = await send_loading_gif(message, t["name_analyzing"])
        try:
            user   = await get_or_create_user(uid)
            prompt = get_name_prompt(user, lang, uid) + text
            result = await groq_ask(prompt)
            try:
                await gif_msg.delete()
            except Exception:
                pass
            await send_long(message, result)
            await increment_uses(uid)
            hint = get_name_hint(user, lang, uid)
            if hint:
                await message.answer(hint, parse_mode="HTML",
                                     reply_markup=paywall_kb(lang))
                user_state[uid].update({"step": "paywall"})
                return
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── Настройка уведомлений — дата рождения ─
    if step == "notify_date":
        user_state[uid].update({"step": "notify_time", "notify_birth": text})
        await message.answer(t["notify_ask_time"])
        return

    # ── Настройка уведомлений — время ──────────
    if step == "notify_time":
        from database import db_pool
        if not re.match(r"^\d{2}:\d{2}$", text):
            await message.answer(t["notify_bad_time"])
            return
        birth_date = state.get("notify_birth", "")
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET birth_date=$1, notify_time=$2, notify_enabled=TRUE WHERE user_id=$3",
                birth_date, text, uid
            )
        user_state[uid].update({"step": "menu"})
        await message.answer(t["notify_saved"].format(time=text))
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    await message.answer(t["unexpected"], reply_markup=menu_kb(lang))