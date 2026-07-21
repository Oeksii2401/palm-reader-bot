from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from config import ADMIN_IDS
from database import (
    get_stats_overview, get_reading_stats, get_referral_stats, get_users_page,
)

router = Router()

# Пагинация списка пользователей — отдельное состояние, не пересекается
# с обычным user_state бота (админ-панель полностью изолирована от логики гаданий).
admin_page: dict = {}

READING_LABELS = {
    "palm": "🖐 Хиромантия",
    "numerology": "🔢 Нумерология",
    "natal": "⭐ Натальная карта",
    "compatibility": "💑 Совместимость",
    "horoscope": "🌟 Гороскоп",
    "name": "🔤 Значение имени",
}

PLAN_LABELS = {1: "Стандарт", 2: "Премиум"}

BTN_OVERVIEW = "📊 Загальна статистика"
BTN_READINGS = "📖 По розділах"
BTN_USERS = "👥 Користувачі"
BTN_REFERRALS = "🔗 Реферали"
BTN_NEXT = "➡️ Далі"
BTN_PREV = "⬅️ Назад"
BTN_CLOSE = "🚪 Закрити адмінку"

ADMIN_BUTTONS = {BTN_OVERVIEW, BTN_READINGS, BTN_USERS, BTN_REFERRALS, BTN_NEXT, BTN_PREV, BTN_CLOSE}


def admin_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=BTN_OVERVIEW)],
        [KeyboardButton(text=BTN_READINGS)],
        [KeyboardButton(text=BTN_USERS)],
        [KeyboardButton(text=BTN_REFERRALS)],
        [KeyboardButton(text=BTN_CLOSE)],
    ], resize_keyboard=True)


def users_nav_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=BTN_PREV), KeyboardButton(text=BTN_NEXT)],
        [KeyboardButton(text=BTN_OVERVIEW)],
        [KeyboardButton(text=BTN_CLOSE)],
    ], resize_keyboard=True)


@router.message(Command("admin"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_admin(message: Message):
    await message.answer("🛠 Адмін-панель. Оберіть розділ:", reply_markup=admin_kb())


@router.message(F.text == BTN_CLOSE, F.from_user.id.in_(ADMIN_IDS))
async def admin_close(message: Message):
    from keyboards import menu_kb
    await message.answer("Адмін-панель закрита.", reply_markup=menu_kb("ru"))


@router.message(F.text == BTN_OVERVIEW, F.from_user.id.in_(ADMIN_IDS))
async def admin_overview(message: Message):
    s = await get_stats_overview()

    def fmt_revenue(rows):
        if not rows:
            return "— немає платежів —"
        lines = []
        for r in rows:
            plan_name = PLAN_LABELS.get(r["plan"], f"plan={r['plan']}")
            lines.append(f"  {r['currency'].upper()} / {plan_name}: {r['cnt']}")
        return "\n".join(lines)

    text = (
        "📊 <b>Загальна статистика</b>\n\n"
        f"👤 Всього користувачів: <b>{s['total_users']}</b>\n"
        f"🆕 Нових сьогодні: {s['new_today']}\n"
        f"🆕 Нових за 7 днів: {s['new_week']}\n\n"
        f"📈 DAU (сьогодні): <b>{s['dau']}</b>\n"
        f"📈 WAU (7 днів): <b>{s['wau']}</b>\n\n"
        f"🔮 Всього гадань: {s['total_readings']}\n"
        f"🔮 Гадань сьогодні: {s['readings_today']}\n\n"
        f"⭐ Активних підписок: <b>{s['active_subs']}</b>\n\n"
        f"💰 Оплати сьогодні:\n{fmt_revenue(s['revenue_today'])}\n\n"
        f"💰 Оплати всього:\n{fmt_revenue(s['revenue_total'])}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=admin_kb())


@router.message(F.text == BTN_READINGS, F.from_user.id.in_(ADMIN_IDS))
async def admin_readings(message: Message):
    rows = await get_reading_stats()
    if not rows:
        await message.answer("📖 Поки що немає жодного гадання.", reply_markup=admin_kb())
        return
    lines = ["📖 <b>Гадання по розділах</b>\n"]
    for r in rows:
        label = READING_LABELS.get(r["reading_type"], r["reading_type"])
        lines.append(f"{label}: <b>{r['cnt']}</b>")
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_kb())


@router.message(F.text == BTN_REFERRALS, F.from_user.id.in_(ADMIN_IDS))
async def admin_referrals(message: Message):
    r = await get_referral_stats()
    total = r["total_referred"] or 0
    converted = r["converted"] or 0
    rate = f"{(converted / total * 100):.1f}%" if total else "—"

    lines = [
        "🔗 <b>Реферальна статистика</b>\n",
        f"👥 Всього залучено рефералів: <b>{total}</b>",
        f"✅ З них оформили підписку: <b>{converted}</b>",
        f"📊 Конверсія: <b>{rate}</b>\n",
        "🏆 <b>Топ рефереров:</b>",
    ]
    if r["top_referrers"]:
        for i, row in enumerate(r["top_referrers"], 1):
            lines.append(f"{i}. ID {row['user_id']} — {row['cnt']} реферал(ів)")
    else:
        lines.append("— поки що немає —")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_kb())


async def _render_users_page(message: Message, uid: int):
    page = admin_page.get(uid, 0)
    offset = page * 10
    rows = await get_users_page(offset=offset, limit=10)

    if not rows and page > 0:
        # Страница пустая (например, пользователей стало меньше) — откатываемся
        admin_page[uid] = page - 1
        return await _render_users_page(message, uid)

    if not rows:
        await message.answer("👥 Користувачів поки що немає.", reply_markup=admin_kb())
        return

    lines = [f"👥 <b>Користувачі</b> (сторінка {page + 1})\n"]
    for u in rows:
        plan_name = PLAN_LABELS.get(u["plan"], "Free") if u["is_subscribed"] else "Free"
        sub_info = ""
        if u["is_subscribed"] and u["sub_until"]:
            sub_info = f", до {u['sub_until'].strftime('%d.%m.%Y')}"
        created = u["created_at"].strftime("%d.%m.%Y") if u["created_at"] else "—"
        lines.append(
            f"• <code>{u['user_id']}</code> | {u['lang']} | {plan_name}{sub_info} "
            f"| гадань: {u['free_uses']} | рег: {created}"
        )

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=users_nav_kb())


@router.message(F.text == BTN_USERS, F.from_user.id.in_(ADMIN_IDS))
async def admin_users(message: Message):
    admin_page[message.from_user.id] = 0
    await _render_users_page(message, message.from_user.id)


@router.message(F.text == BTN_NEXT, F.from_user.id.in_(ADMIN_IDS))
async def admin_users_next(message: Message):
    uid = message.from_user.id
    admin_page[uid] = admin_page.get(uid, 0) + 1
    await _render_users_page(message, uid)


@router.message(F.text == BTN_PREV, F.from_user.id.in_(ADMIN_IDS))
async def admin_users_prev(message: Message):
    uid = message.from_user.id
    admin_page[uid] = max(0, admin_page.get(uid, 0) - 1)
    await _render_users_page(message, uid)
