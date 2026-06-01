import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, PreCheckoutQuery

from database import get_or_create_user, activate_subscription, give_ref_bonus
from texts import TEXTS
from keyboards import menu_kb
from state import user_state

router = Router()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    uid     = message.from_user.id
    payload = message.successful_payment.invoice_payload
    lang    = user_state.get(uid, {}).get("lang", "ru")
    t       = TEXTS[lang]

    plan = 1 if payload == "standard" else 2
    await activate_subscription(uid, plan)

    # Реферальные бонусы
    user = await get_or_create_user(uid)
    if user.get('referred_by'):
        ref_l1 = user['referred_by']
        await give_ref_bonus(ref_l1, 30)
        ru1 = await get_or_create_user(ref_l1)
        try:
            await message.bot.send_message(
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
                await message.bot.send_message(
                    ref_l2,
                    TEXTS[ru2.get('lang') or 'ru']['ref_bonus_msg'].format(days=10),
                    parse_mode="HTML"
                )
            except Exception:
                pass

    key = 'pay_success_premium' if plan == 2 else 'pay_success_standard'
    await message.answer(t[key], parse_mode="HTML")
    user_state[uid] = {"lang": lang, "step": "menu"}
    await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
