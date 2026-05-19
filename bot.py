import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

SYSTEM_PROMPT = """
Ты — опытный хиромант по имени Аарон с 25-летним опытом.
Стиль общения: тёплый, атмосферный, с душой и лёгким добрым юмором.
Никогда не пугаешь человека.
Анализируй фото ладони по классической хиромантии.
Различай активную (обычно правая) и пассивную руку (левая).
Используй эмодзи, делай ответ красивым и понятным.
В конце всегда давай 1-2 добрых совета.
"""

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 Привет! Я Аарон — хиромант.\n\n"
        "Пришли мне чёткое фото ладони (одну или обе), и я расскажу, что они говорят о тебе ✨"
    )

@dp.message(F.photo)
async def handle_photo(message: Message):
    await message.answer("✨ Анализирую твою ладонь... Подожди немного.")
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = f"photo_{message.from_user.id}.jpg"
    await bot.download_file(file.file_path, file_path)
    try:
        img = genai.upload_file(path=file_path)
        response = model.generate_content([
            SYSTEM_PROMPT, img,
            "\nОпиши подробно эту ладонь. Определи активная это рука или пассивная."
        ])
        await message.answer(response.text)
    except Exception as e:
        await message.answer("😔 Не получилось разобрать фото. Попробуй прислать другое — лучше освещение, без бликов.")
    if os.path.exists(file_path):
        os.remove(file_path)

async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
