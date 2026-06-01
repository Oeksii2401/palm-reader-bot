import base64
import logging
import os
import google.generativeai as genai

from aiogram import Router, F
from aiogram.types import Message

from config import GEMINI_API_KEY
from database import increment_uses
from texts import TEXTS
from keyboards import menu_kb, back_kb
from prompts import PALM_SYSTEM, PALM_PROMPTS
from utils import send_long, send_loading_gif
from state import user_state

router = Router()

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')


def get_state(uid):
    return user_state.get(uid, {"lang": "ru", "step": "menu"})


@router.message(F.photo)
async def handle_photo(message: Message):
    uid   = message.from_user.id
    state = get_state(uid)
    lang  = state.get("lang", "ru")
    step  = state.get("step", "menu")
    t     = TEXTS[lang]

    if step not in ("palm_photo", "palm_left", "palm_right"):
        await message.answer(t["unexpected"], reply_markup=menu_kb(lang))
        return

    photo = message.photo[-1]
    file  = await message.bot.get_file(photo.file_id)
    path  = f"photo_{uid}.jpg"
    await message.bot.download_file(file.file_path, path)
    with open(path, "rb") as f:
        img = base64.b64encode(f.read()).decode()
    if os.path.exists(path):
        os.remove(path)

    # Первое фото (обе руки)
    if step == "palm_left":
        user_state[uid].update({"step": "palm_right", "left_img": img})
        await message.answer(t["send_second"])
        return

    # Второе фото (обе руки) — Gemini
    if step == "palm_right":
        gif_msg  = await send_loading_gif(message, t["analyzing_both"])
        left_img = state.get("left_img", "")
        try:
            resp = gemini_model.generate_content([
                PALM_SYSTEM[lang],
                {"inline_data": {"mime_type": "image/jpeg", "data": left_img}},
                {"inline_data": {"mime_type": "image/jpeg", "data": img}},
                PALM_PROMPTS[lang]["both"]
            ])
            try:
                await gif_msg.delete()
            except Exception:
                pass
            await send_long(message, resp.text)
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["palm_error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # Одна рука — Gemini
    hand    = state.get("hand", "right")
    gif_msg = await send_loading_gif(message, t["analyzing"])
    try:
        resp = gemini_model.generate_content([
            PALM_SYSTEM[lang],
            {"inline_data": {"mime_type": "image/jpeg", "data": img}},
            PALM_PROMPTS[lang][hand]
        ])
        try:
            await gif_msg.delete()
        except Exception:
            pass
        await send_long(message, resp.text)
        await increment_uses(uid)
    except Exception as e:
        logging.error(e)
        await message.answer(t["palm_error"])

    user_state[uid].update({"step": "menu"})
    await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
