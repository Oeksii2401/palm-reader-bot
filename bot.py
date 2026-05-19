import asyncio
import logging
import os
import base64
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

# Хранилище состояний пользователей
user_state = {}

# Тексты на разных языках
TEXTS = {
    "uk": {
        "welcome": "👋 Привіт! Я Аарон — хіромант.\n\nОберіть мову / Choose language:",
        "choose_hand": "🖐 Яку руку бажаєте гадати?\n\nПам'ятайте:\n• Права рука — активна (теперішнє і майбутнє)\n• Ліва рука — пасивна (потенціал і минуле)",
        "left_btn": "🤚 Ліва рука",
        "right_btn": "✋ Права рука",
        "both_btn": "🙌 Обидві руки",
        "send_left": "📸 Надішліть фото ЛІВОЇ руки",
        "send_right": "📸 Надішліть фото ПРАВОЇ руки",
        "analyzing": "✨ Аналізую вашу долоню... Зачекайте трохи.",
        "analyzing_both": "✨ Аналізую обидві долоні...",
        "send_second": "📸 Чудово! Тепер надішліть фото ПРАВОЇ руки",
        "error": "😔 Не вдалося проаналізувати фото. Спробуйте інше — краще освітлення, без відблисків.",
        "prompt_left": "Це ЛІВА (пасивна) рука користувача. Проаналізуй її як пасивну руку — природний потенціал, минуле, спадковість.",
        "prompt_right": "Це ПРАВА (активна) рука користувача. Проаналізуй її як активну руку — теперішнє, майбутнє, реалізований потенціал.",
        "prompt_both": "Це ДВІ долоні користувача. Перше фото — ЛІВА (пасивна) рука, друге — ПРАВА (активна). Порівняй обидві та дай повний аналіз.",
    },
    "ru": {
        "welcome": "👋 Привет! Я Аарон — хиромант.\n\nВыберите язык / Choose language:",
        "choose_hand": "🖐 Какую руку хотите погадать?\n\nПомните:\n• Правая рука — активная (настоящее и будущее)\n• Левая рука — пассивная (потенциал и прошлое)",
        "left_btn": "🤚 Левая рука",
        "right_btn": "✋ Правая рука",
        "both_btn": "🙌 Обе руки",
        "send_left": "📸 Пришлите фото ЛЕВОЙ руки",
        "send_right": "📸 Пришлите фото ПРАВОЙ руки",
        "analyzing": "✨ Анализирую вашу ладонь... Подождите немного.",
        "analyzing_both": "✨ Анализирую обе ладони...",
        "send_second": "📸 Отлично! Теперь пришлите фото ПРАВОЙ руки",
        "error": "😔 Не получилось разобрать фото. Попробуйте другое — лучше освещение, без бликов.",
        "prompt_left": "Это ЛЕВАЯ (пассивная) рука пользователя. Анализируй как пассивную руку — природный потенциал, прошлое, наследственность.",
        "prompt_right": "Это ПРАВАЯ (активная) рука пользователя. Анализируй как активную руку — настоящее, будущее, реализованный потенциал.",
        "prompt_both": "Это ДВЕ ладони пользователя. Первое фото — ЛЕВАЯ (пассивная) рука, второе — ПРАВАЯ (активная). Сравни обе и дай полный анализ.",
    },
    "en": {
        "welcome": "👋 Hi! I'm Aaron — a palmist.\n\nChoose language / Оберіть мову:",
        "choose_hand": "🖐 Which hand would you like me to read?\n\nRemember:\n• Right hand — active (present & future)\n• Left hand — passive (potential & past)",
        "left_btn": "🤚 Left hand",
        "right_btn": "✋ Right hand",
        "both_btn": "🙌 Both hands",
        "send_left": "📸 Please send a photo of your LEFT hand",
        "send_right": "📸 Please send a photo of your RIGHT hand",
        "analyzing": "✨ Analyzing your palm... Please wait.",
        "analyzing_both": "✨ Analyzing both palms...",
        "send_second": "📸 Great! Now send a photo of your RIGHT hand",
        "error": "😔 Couldn't analyze the photo. Try another — better lighting, no glare.",
        "prompt_left": "This is the LEFT (passive) hand. Analyze it as the passive hand — natural potential, past, hereditary traits.",
        "prompt_right": "This is the RIGHT (active) hand. Analyze it as the active hand — present, future, realized potential.",
        "prompt_both": "These are BOTH palms. First photo — LEFT (passive) hand, second — RIGHT (active). Compare both and give a full reading.",
    },
    "de": {
        "welcome": "👋 Hallo! Ich bin Aaron — ein Handleser.\n\nSprache wählen / Choose language:",
        "choose_hand": "🖐 Welche Hand möchten Sie lesen lassen?\n\nDenken Sie daran:\n• Rechte Hand — aktiv (Gegenwart & Zukunft)\n• Linke Hand — passiv (Potenzial & Vergangenheit)",
        "left_btn": "🤚 Linke Hand",
        "right_btn": "✋ Rechte Hand",
        "both_btn": "🙌 Beide Hände",
        "send_left": "📸 Bitte senden Sie ein Foto Ihrer LINKEN Hand",
        "send_right": "📸 Bitte senden Sie ein Foto Ihrer RECHTEN Hand",
        "analyzing": "✨ Analysiere Ihre Handfläche... Bitte warten.",
        "analyzing_both": "✨ Analysiere beide Handflächen...",
        "send_second": "📸 Super! Jetzt senden Sie ein Foto Ihrer RECHTEN Hand",
        "error": "😔 Foto konnte nicht analysiert werden. Versuchen Sie ein anderes — bessere Beleuchtung, kein Blendlicht.",
        "prompt_left": "Dies ist die LINKE (passive) Hand. Analysiere sie als passive Hand — natürliches Potenzial, Vergangenheit, Erbmerkmale.",
        "prompt_right": "Dies ist die RECHTE (aktive) Hand. Analysiere sie als aktive Hand — Gegenwart, Zukunft, realisiertes Potenzial.",
        "prompt_both": "Dies sind BEIDE Handflächen. Erstes Foto — LINKE (passive) Hand, zweites — RECHTE (aktive). Vergleiche beide und gib eine vollständige Lesung.",
    }
}

SYSTEM_PROMPT = {
    "uk": "Ти — досвідчений хіромант на ім'я Аарон з 25-річним досвідом. Стиль: теплий, атмосферний, з душею та легким добрим гумором. Ніколи не лякай людину. Аналізуй долоню за класичною хіромантією. Використовуй емодзі. Наприкінці давай 1-2 добрі поради. Відповідай УКРАЇНСЬКОЮ мовою.",
    "ru": "Ты — опытный хиромант по имени Аарон с 25-летним опытом. Стиль: тёплый, атмосферный, с душой и лёгким добрым юмором. Никогда не пугай человека. Анализируй ладонь по классической хиромантии. Используй эмодзи. В конце давай 1-2 добрых совета. Отвечай на РУССКОМ языке.",
    "en": "You are an experienced palmist named Aaron with 25 years of experience. Style: warm, atmospheric, soulful with light humor. Never frighten the person. Analyze the palm using classical palmistry. Use emojis. End with 1-2 kind pieces of advice. Reply in ENGLISH.",
    "de": "Du bist ein erfahrener Handleser namens Aaron mit 25 Jahren Erfahrung. Stil: warm, atmosphärisch, einfühlsam mit leichtem Humor. Erschrecke die Person niemals. Analysiere die Handfläche nach klassischer Handlesekunst. Verwende Emojis. Beende mit 1-2 freundlichen Ratschlägen. Antworte auf DEUTSCH."
}

def lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="🇺🇦 Українська"),
            KeyboardButton(text="🇷🇺 Русский"),
        ], [
            KeyboardButton(text="🇬🇧 English"),
            KeyboardButton(text="🇩🇪 Deutsch"),
        ]],
        resize_keyboard=True
    )

def hand_keyboard(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text=t["left_btn"]),
            KeyboardButton(text=t["right_btn"]),
        ], [
            KeyboardButton(text=t["both_btn"]),
        ]],
        resize_keyboard=True
    )

async def send_long_message(message: Message, text: str):
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await message.answer(text[i:i+4000])
    else:
        await message.answer(text)

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 Вітаю / Привет / Hello / Hallo!\n\nОберіть мову / Выберите язык / Choose language / Sprache wählen:",
        reply_markup=lang_keyboard()
    )

@dp.message(F.text.in_(["🇺🇦 Українська", "🇷🇺 Русский", "🇬🇧 English", "🇩🇪 Deutsch"]))
async def choose_language(message: Message):
    lang_map = {
        "🇺🇦 Українська": "uk",
        "🇷🇺 Русский": "ru",
        "🇬🇧 English": "en",
        "🇩🇪 Deutsch": "de"
    }
    lang = lang_map[message.text]
    uid = message.from_user.id
    user_state[uid] = {"lang": lang, "step": "choose_hand"}
    t = TEXTS[lang]
    await message.answer(t["choose_hand"], reply_markup=hand_keyboard(lang))

@dp.message(F.photo)
async def handle_photo(message: Message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    lang = state.get("lang", "ru")
    t = TEXTS[lang]
    step = state.get("step", "choose_hand")

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = f"photo_{uid}.jpg"
    await bot.download_file(file.file_path, file_path)

    with open(file_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    if os.path.exists(file_path):
        os.remove(file_path)

    # Если ждём вторую руку
    if step == "wait_right":
        await message.answer(t["analyzing_both"])
        first_img = state.get("left_photo")
        try:
            response = model.generate_content([
                SYSTEM_PROMPT[lang],
                {"inline_data": {"mime_type": "image/jpeg", "data": first_img}},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_data}},
                t["prompt_both"]
            ])
            await send_long_message(message, response.text)
        except Exception as e:
            logging.error(f"Error: {e}")
            await message.answer(f"Ошибка: {str(e)[:200]}")
        user_state[uid]["step"] = "choose_hand"
        await message.answer(t["choose_hand"], reply_markup=hand_keyboard(lang))
        return

    # Одна рука
    hand = state.get("hand", "right")
    prompt = t["prompt_left"] if hand == "left" else t["prompt_right"]
    await message.answer(t["analyzing"])

    try:
        response = model.generate_content([
            SYSTEM_PROMPT[lang],
            {"inline_data": {"mime_type": "image/jpeg", "data": img_data}},
            prompt
        ])
        await send_long_message(message, response.text)
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer(f"Ошибка: {str(e)[:200]}")

    user_state[uid]["step"] = "choose_hand"
    await message.answer(t["choose_hand"], reply_markup=hand_keyboard(lang))

@dp.message(F.text)
async def handle_text(message: Message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    lang = state.get("lang", "ru")
    t = TEXTS[lang]

    left_variants = [TEXTS[l]["left_btn"] for l in TEXTS]
    right_variants = [TEXTS[l]["right_btn"] for l in TEXTS]
    both_variants = [TEXTS[l]["both_btn"] for l in TEXTS]

    if message.text in left_variants:
        user_state[uid] = {**state, "hand": "left", "step": "wait_photo"}
        await message.answer(t["send_left"])
    elif message.text in right_variants:
        user_state[uid] = {**state, "hand": "right", "step": "wait_photo"}
        await message.answer(t["send_right"])
    elif message.text in both_variants:
        user_state[uid] = {**state, "hand": "both", "step": "wait_left"}
        await message.answer(t["send_left"])

async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
