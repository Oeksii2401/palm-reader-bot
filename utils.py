import asyncio
import logging
from aiogram.types import Message
from config import LOADING_GIF_URL, GROQ_API_KEY, GROQ_MODEL
from groq import Groq

groq_client = Groq(api_key=GROQ_API_KEY)


async def send_long(msg: Message, text: str):
    """Отправляет длинный текст частями по 4000 символов."""
    for i in range(0, len(text), 4000):
        await msg.answer(text[i:i + 4000])


async def send_loading_gif(message: Message, caption: str) -> Message:
    """Отправляет GIF загрузки с подписью."""
    try:
        return await message.answer_animation(
            animation=LOADING_GIF_URL,
            caption=caption
        )
    except Exception:
        return await message.answer(caption)


def groq_ask_sync(prompt: str) -> str:
    """Синхронный вызов Groq."""
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
    )
    return response.choices[0].message.content


async def groq_ask(prompt: str) -> str:
    """Асинхронная обёртка для Groq."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, groq_ask_sync, prompt)