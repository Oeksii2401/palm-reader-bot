import logging
from aiogram import Router, F
from aiogram.types import Message, PreCheckoutQuery

from config import CRYPTO_ASSET, CRYPTO_STANDARD_PRICE, CRYPTO_PREMIUM_PRICE
from database import (
    get_or_create_user, activate_subscription, give_ref_bonus,
    create_crypto_invoice, get_latest_pending_invoice, mark_crypto_invoice_status,
)
from texts import TEXTS
from keyboards import (
    menu_kb, crypto_wait_kb,
    ALL_STANDARD_CRYPTO_BTNS, ALL_PREMIUM_CRYPTO_BTNS, ALL_CRYPTO_CHECK_BTNS,
)
from state import user_state, get_state
import crypto_pay

router = Router()


async def apply_subscription_payment(bot, uid: int, plan: int, lang: str):
    """
    Общая логика активации подписки после ЛЮБОЙ успешной оплаты
    (Stars или крипта): начисление подписки, реферальные бонусы,
    уведомления, сброс состояния в главное меню.
    """
    t = TEXTS[lang]
    await activate_subscription(uid, plan)

    user = await get_or_create_user(uid)
    if user.get('referred_by'):
        ref_l1 = user['referred_by']
        await give_ref_bonus(ref_l1, 30)
        ru1 = await get_or_create_user(ref_l1)
        try:
            await bot.send_message(
                ref_l1,
                TEXTS[ru1.get('lang') or 'ru']['ref_bonus_msg'].format(days=30),
                parse_mode="HTML"
            )
        except Exception:
            pass
        if ru1.get('referred_by'):
            ref_l2 = ru1['referred_by']
            await give_ref_bonus(ref_l2, 10)
            ru2 = await get_or_create_user(ref_l2)
            try:
                await bot.send_message(
                    ref_l2,
                    TEXTS[ru2.get('lang') or 'ru']['ref_bonus_msg'].format(days=10),
                    parse_mode="HTML"
                )
            except Exception:
                pass

    key = 'pay_success_premium' if plan == 2 else 'pay_success_standard'
    await bot.send_message(uid, t[key], parse_mode="HTML")
    user_state[uid] = {"lang": lang, "step": "menu"}
    await bot.send_message(uid, t["choose_menu"], reply_markup=menu_kb(lang))


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    uid     = message.from_user.id
    payload = message.successful_payment.invoice_payload
    lang    = user_state.get(uid, {}).get("lang", "ru")

    plan = 1 if payload == "standard" else 2
    await apply_subscription_payment(message.bot, uid, plan, lang)


# ── Оплата криптой: выбор плана → создание инвойса ───────────────
@router.message(F.text.in_(ALL_STANDARD_CRYPTO_BTNS | ALL_PREMIUM_CRYPTO_BTNS))
async def crypto_plan_selected(message: Message):
    uid   = message.from_user.id
    state = get_state(uid)
    lang  = state.get("lang", "ru")
    t     = TEXTS[lang]
    text  = message.text.strip()

    is_premium = text in ALL_PREMIUM_CRYPTO_BTNS
    plan_str   = "premium" if is_premium else "standard"
    amount     = CRYPTO_PREMIUM_PRICE if is_premium else CRYPTO_STANDARD_PRICE
    description = "Aaron Palmreader — Premium (30 days)" if is_premium else "Aaron Palmreader — Standard (30 days)"

    result = await crypto_pay.create_invoice(
        amount=amount,
        asset=CRYPTO_ASSET,
        description=description,
        payload=f"{uid}:{plan_str}",
    )

    if not result or not result.get("invoice_id"):
        await message.answer(t["crypto_error"])
        return

    invoice_id = result["invoice_id"]
    pay_url    = result.get("bot_invoice_url") or result.get("pay_url") or ""

    await create_crypto_invoice(invoice_id, uid, plan_str, amount, CRYPTO_ASSET)
    state.update({"step": "crypto_wait", "pending_invoice_id": invoice_id})

    await message.answer(
        t["crypto_invoice_msg"].format(amount=amount, url=pay_url),
        reply_markup=crypto_wait_kb(lang),
        disable_web_page_preview=True,
    )


# ── Оплата криптой: проверка статуса по кнопке ───────────────────
@router.message(F.text.in_(ALL_CRYPTO_CHECK_BTNS))
async def crypto_check_payment(message: Message):
    uid   = message.from_user.id
    state = get_state(uid)
    lang  = state.get("lang", "ru")
    t     = TEXTS[lang]

    invoice_id = state.get("pending_invoice_id")
    if not invoice_id:
        invoice = await get_latest_pending_invoice(uid)
        if not invoice:
            await message.answer(t["crypto_error"])
            return
        invoice_id = invoice["invoice_id"]

    status = await crypto_pay.get_invoice_status(invoice_id)

    if status == "paid":
        invoice = await get_latest_pending_invoice(uid)
        plan_str = invoice["plan"] if invoice else state.get("pending_plan", "standard")
        plan = 2 if plan_str == "premium" else 1
        await mark_crypto_invoice_status(invoice_id, "paid")
        await apply_subscription_payment(message.bot, uid, plan, lang)
        return

    if status == "expired":
        await mark_crypto_invoice_status(invoice_id, "expired")
        await message.answer(t["crypto_error"])
        state.update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    await message.answer(t["crypto_still_pending"])
