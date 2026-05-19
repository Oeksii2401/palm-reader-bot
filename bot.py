import asyncio
import logging
import os
import base64
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

user_state = {}

# ─────────────────────────────────────────────
# ТЕКСТЫ
# ─────────────────────────────────────────────
TEXTS = {
    "uk": {
        "choose_lang":     "🔮 Оберіть мову / Choose language:",
        "choose_menu":     "🔮 Що бажаєте дізнатися?",
        "menu_palm":       "🖐 Хіромантія",
        "menu_num":        "🔢 Нумерологія",
        "menu_natal":      "⭐ Натальна карта",
        "menu_compat":     "💑 Сумісність",
        "menu_horoscope":  "🌟 Гороскоп",
        "back":            "↩️ Головне меню",
        "choose_hand":     "🖐 Яку руку гадаємо?\n\n• Права — активна (теперішнє і майбутнє)\n• Ліва — пасивна (потенціал і минуле)",
        "left_btn":        "🤚 Ліва рука",
        "right_btn":       "✋ Права рука",
        "both_btn":        "🙌 Обидві руки",
        "send_left":       "📸 Надішліть фото ЛІВОЇ руки (долоня вгору, гарне освітлення)",
        "send_right":      "📸 Надішліть фото ПРАВОЇ руки (долоня вгору, гарне освітлення)",
        "send_second":     "📸 Чудово! Тепер надішліть фото ПРАВОЇ руки",
        "analyzing":       "✨ Читаю лінії долі... Зачекайте.",
        "analyzing_both":  "✨ Порівнюю обидві долоні...",
        "palm_error":      "😔 Не вдалося розібрати фото. Спробуйте інше — пряме освітлення, долоня чітко видна.",
        "num_ask":         "🔢 Введіть ПОВНЕ ім'я та дату народження через кому:\n\nПриклад:\nІван Петренко Олексійович, 15.03.1990",
        "num_analyzing":   "🔢 Розраховую нумерологічний портрет...",
        "natal_ask":       "⭐ Введіть дату, час та місце народження:\n\nПриклад:\n15.03.1990, 14:30, Київ\n\n(Час невідомий — напишіть 12:00)",
        "natal_analyzing": "⭐ Будую натальну карту...",
        "compat_ask1":     "💑 Введіть дані ПЕРШОЇ людини (ім'я та дата):\n\nПриклад:\nМарія, 15.03.1990",
        "compat_ask2":     "💑 Тепер введіть дані ДРУГОЇ людини:\n\nПриклад:\nОлексій, 22.07.1988",
        "compat_analyzing":"💑 Аналізую сумісність...",
        "horoscope_ask":   "🌟 Введіть дату народження:\n\nПриклад: 15.03.1990",
        "horoscope_calc":  "🌟 Складаю гороскоп на сьогодні та завтра...",
        "error":           "😔 Щось пішло не так. Спробуйте ще раз.",
        "unexpected":      "Скористайтеся кнопками меню 👇",
    },
    "ru": {
        "choose_lang":     "🔮 Выберите язык / Choose language:",
        "choose_menu":     "🔮 Что желаете узнать?",
        "menu_palm":       "🖐 Хиромантия",
        "menu_num":        "🔢 Нумерология",
        "menu_natal":      "⭐ Натальная карта",
        "menu_compat":     "💑 Совместимость",
        "menu_horoscope":  "🌟 Гороскоп",
        "back":            "↩️ Главное меню",
        "choose_hand":     "🖐 Какую руку читаем?\n\n• Правая — активная (настоящее и будущее)\n• Левая — пассивная (потенциал и прошлое)",
        "left_btn":        "🤚 Левая рука",
        "right_btn":       "✋ Правая рука",
        "both_btn":        "🙌 Обе руки",
        "send_left":       "📸 Пришлите фото ЛЕВОЙ руки (ладонь вверх, хорошее освещение)",
        "send_right":      "📸 Пришлите фото ПРАВОЙ руки (ладонь вверх, хорошее освещение)",
        "send_second":     "📸 Отлично! Теперь пришлите фото ПРАВОЙ руки",
        "analyzing":       "✨ Читаю линии судьбы... Подождите.",
        "analyzing_both":  "✨ Сравниваю обе ладони...",
        "palm_error":      "😔 Не удалось разобрать фото. Попробуйте другое — прямое освещение, ладонь чётко видна.",
        "num_ask":         "🔢 Введите ПОЛНОЕ имя и дату рождения через запятую:\n\nПример:\nИван Петров Алексеевич, 15.03.1990",
        "num_analyzing":   "🔢 Рассчитываю нумерологический портрет...",
        "natal_ask":       "⭐ Введите дату, время и место рождения:\n\nПример:\n15.03.1990, 14:30, Киев\n\n(Время неизвестно — напишите 12:00)",
        "natal_analyzing": "⭐ Строю натальную карту...",
        "compat_ask1":     "💑 Введите данные ПЕРВОГО человека (имя и дата):\n\nПример:\nМария, 15.03.1990",
        "compat_ask2":     "💑 Теперь введите данные ВТОРОГО человека:\n\nПример:\nАлексей, 22.07.1988",
        "compat_analyzing":"💑 Анализирую совместимость...",
        "horoscope_ask":   "🌟 Введите дату рождения:\n\nПример: 15.03.1990",
        "horoscope_calc":  "🌟 Составляю гороскоп на сегодня и завтра...",
        "error":           "😔 Что-то пошло не так. Попробуйте ещё раз.",
        "unexpected":      "Используйте кнопки меню 👇",
    },
    "en": {
        "choose_lang":     "🔮 Choose language / Оберіть мову:",
        "choose_menu":     "🔮 What would you like to explore?",
        "menu_palm":       "🖐 Palmistry",
        "menu_num":        "🔢 Numerology",
        "menu_natal":      "⭐ Natal Chart",
        "menu_compat":     "💑 Compatibility",
        "menu_horoscope":  "🌟 Horoscope",
        "back":            "↩️ Main Menu",
        "choose_hand":     "🖐 Which hand shall we read?\n\n• Right — active (present & future)\n• Left — passive (potential & past)",
        "left_btn":        "🤚 Left hand",
        "right_btn":       "✋ Right hand",
        "both_btn":        "🙌 Both hands",
        "send_left":       "📸 Send a photo of your LEFT hand (palm up, good lighting)",
        "send_right":      "📸 Send a photo of your RIGHT hand (palm up, good lighting)",
        "send_second":     "📸 Great! Now send a photo of your RIGHT hand",
        "analyzing":       "✨ Reading the lines of fate... Please wait.",
        "analyzing_both":  "✨ Comparing both palms...",
        "palm_error":      "😔 Couldn't analyze the photo. Try again — direct lighting, palm clearly visible.",
        "num_ask":         "🔢 Enter your FULL name and date of birth:\n\nExample:\nJohn Alexander Smith, 15.03.1990",
        "num_analyzing":   "🔢 Calculating your numerological portrait...",
        "natal_ask":       "⭐ Enter date, time and place of birth:\n\nExample:\n15.03.1990, 14:30, London\n\n(Time unknown — write 12:00)",
        "natal_analyzing": "⭐ Building your natal chart...",
        "compat_ask1":     "💑 Enter FIRST person's details (name and date):\n\nExample:\nMaria, 15.03.1990",
        "compat_ask2":     "💑 Now enter SECOND person's details:\n\nExample:\nAlex, 22.07.1988",
        "compat_analyzing":"💑 Analyzing compatibility...",
        "horoscope_ask":   "🌟 Enter your date of birth:\n\nExample: 15.03.1990",
        "horoscope_calc":  "🌟 Preparing your horoscope for today and tomorrow...",
        "error":           "😔 Something went wrong. Please try again.",
        "unexpected":      "Please use the menu buttons 👇",
    },
    "de": {
        "choose_lang":     "🔮 Sprache wählen / Choose language:",
        "choose_menu":     "🔮 Was möchten Sie erkunden?",
        "menu_palm":       "🖐 Handlesen",
        "menu_num":        "🔢 Numerologie",
        "menu_natal":      "⭐ Geburtshoroskop",
        "menu_compat":     "💑 Partnerschaft",
        "menu_horoscope":  "🌟 Horoskop",
        "back":            "↩️ Hauptmenü",
        "choose_hand":     "🖐 Welche Hand lesen wir?\n\n• Rechte — aktiv (Gegenwart & Zukunft)\n• Linke — passiv (Potenzial & Vergangenheit)",
        "left_btn":        "🤚 Linke Hand",
        "right_btn":       "✋ Rechte Hand",
        "both_btn":        "🙌 Beide Hände",
        "send_left":       "📸 Senden Sie ein Foto Ihrer LINKEN Hand (Handfläche oben, gute Beleuchtung)",
        "send_right":      "📸 Senden Sie ein Foto Ihrer RECHTEN Hand (Handfläche oben, gute Beleuchtung)",
        "send_second":     "📸 Wunderbar! Jetzt senden Sie ein Foto Ihrer RECHTEN Hand",
        "analyzing":       "✨ Lese die Schicksalslinien... Bitte warten.",
        "analyzing_both":  "✨ Vergleiche beide Handflächen...",
        "palm_error":      "😔 Foto konnte nicht analysiert werden. Bitte erneut versuchen.",
        "num_ask":         "🔢 Geben Sie Ihren VOLLSTÄNDIGEN Namen und Geburtsdatum ein:\n\nBeispiel:\nHans Friedrich Müller, 15.03.1990",
        "num_analyzing":   "🔢 Berechne Ihr numerologisches Porträt...",
        "natal_ask":       "⭐ Geben Sie Datum, Uhrzeit und Geburtsort ein:\n\nBeispiel:\n15.03.1990, 14:30, Berlin\n\n(Zeit unbekannt — schreiben Sie 12:00)",
        "natal_analyzing": "⭐ Erstelle Ihr Geburtshoroskop...",
        "compat_ask1":     "💑 Geben Sie Daten der ERSTEN Person ein:\n\nBeispiel:\nMaria, 15.03.1990",
        "compat_ask2":     "💑 Jetzt Daten der ZWEITEN Person:\n\nBeispiel:\nAlex, 22.07.1988",
        "compat_analyzing":"💑 Analysiere die Kompatibilität...",
        "horoscope_ask":   "🌟 Geben Sie Ihr Geburtsdatum ein:\n\nBeispiel: 15.03.1990",
        "horoscope_calc":  "🌟 Erstelle Ihr Horoskop für heute und morgen...",
        "error":           "😔 Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.",
        "unexpected":      "Bitte verwenden Sie die Menü-Schaltflächen 👇",
    }
}

# ─────────────────────────────────────────────
# ПРОМТЫ
# ─────────────────────────────────────────────
PALM_SYSTEM = {
    "uk": "Ти — Аарон, майстер-хіромант із 25-річним досвідом. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ. СТРУКТУРА: 1)Тип руки та загальна енергетика 2)Лінія Життя 3)Лінія Серця 4)Лінія Голови 5)Лінія Долі 6)Горби 7)Пальці 8)Загальний висновок 9)3 конкретні поради. Стиль: глибокий, серйозний, мудрий наставник з теплою усмішкою. Використовуй емодзі.",
    "ru": "Ты — Аарон, мастер-хиромант с 25-летним опытом. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ. СТРУКТУРА: 1)Тип руки и общая энергетика 2)Линия Жизни 3)Линия Сердца 4)Линия Головы 5)Линия Судьбы 6)Холмы 7)Пальцы 8)Общий вывод 9)3 конкретных совета. Стиль: глубокий, серьёзный, мудрый наставник с доброй улыбкой. Используй эмодзи.",
    "en": "You are Aaron, a master palmist with 25 years of experience. Reply EXCLUSIVELY IN ENGLISH. STRUCTURE: 1)Hand type & energy 2)Life Line 3)Heart Line 4)Head Line 5)Fate Line 6)Mounts 7)Fingers 8)Overall conclusion 9)3 specific pieces of advice. Style: deep, serious, wise mentor with a warm smile. Use emojis.",
    "de": "Du bist Aaron, ein Meister-Handleser mit 25 Jahren Erfahrung. Antworte AUSSCHLIESSLICH AUF DEUTSCH. STRUKTUR: 1)Handtyp & Energie 2)Lebenslinie 3)Herzlinie 4)Kopflinie 5)Schicksalslinie 6)Hügel 7)Finger 8)Gesamtschluss 9)3 konkrete Ratschläge. Stil: tiefgründig, ernsthaft, weiser Mentor mit warmem Lächeln. Verwende Emojis.",
}
PALM_PROMPTS = {
    "uk": {"left": "ЛІВА (пасивна) рука — природжений потенціал, карма, спадковість. Що дано від народження?", "right": "ПРАВА (активна) рука — реалізація, теперішнє, майбутні можливості. Що людина зробила зі своїм потенціалом?", "both": "Перше фото ЛІВА рука, друге ПРАВА. Порівняй обидві: де реалізовано потенціал, де є резерви?"},
    "ru": {"left": "ЛЕВАЯ (пассивная) рука — врождённый потенциал, карма, наследственность. Что дано от природы?", "right": "ПРАВАЯ (активная) рука — реализация, настоящее, будущие возможности. Что человек сделал со своим потенциалом?", "both": "Первое фото ЛЕВАЯ рука, второе ПРАВАЯ. Сравни обе: где реализован потенциал, где есть резервы?"},
    "en": {"left": "LEFT (passive) hand — innate potential, karma, heredity. What was given by nature?", "right": "RIGHT (active) hand — realization, present, future opportunities. What has this person done with their potential?", "both": "First photo LEFT hand, second RIGHT. Compare both: where is potential fulfilled, where are there reserves?"},
    "de": {"left": "LINKE (passive) Hand — angeborenes Potenzial, Karma, Erbschaft. Was wurde von der Natur gegeben?", "right": "RECHTE (aktive) Hand — Realisierung, Gegenwart, zukünftige Möglichkeiten. Was hat die Person mit ihrem Potenzial gemacht?", "both": "Erstes Foto LINKE Hand, zweites RECHTE. Vergleiche beide: Wo ist Potenzial erfüllt, wo gibt es Reserven?"},
}
NUMEROLOGY_PROMPT = {
    "uk": "Ти — Аарон, майстер нумерології. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ. Розрахуй: 1)Число Життєвого Шляху 2)Число Долі 3)Число Душі 4)Число Особистості 5)Особисте Число Року. Покажи всі розрахунки. Глибоке тлумачення кожного числа. 3 конкретні поради в кінці. Дані: ",
    "ru": "Ты — Аарон, мастер нумерологии. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ. Рассчитай: 1)Число Жизненного Пути 2)Число Судьбы 3)Число Души 4)Число Личности 5)Личное Число Года. Покажи все расчёты. Глубокое толкование каждого числа. 3 конкретных совета в конце. Данные: ",
    "en": "You are Aaron, a master numerologist. Reply EXCLUSIVELY IN ENGLISH. Calculate: 1)Life Path Number 2)Destiny Number 3)Soul Number 4)Personality Number 5)Personal Year Number. Show all calculations. Deep interpretation of each number. 3 specific recommendations at the end. Data: ",
    "de": "Du bist Aaron, ein Meister-Numerologe. Antworte AUSSCHLIESSLICH AUF DEUTSCH. Berechne: 1)Lebenspfadzahl 2)Schicksalszahl 3)Seelenzahl 4)Persönlichkeitszahl 5)Persönliche Jahreszahl. Zeige alle Berechnungen. Tiefe Interpretation jeder Zahl. 3 konkrete Empfehlungen am Ende. Daten: ",
}
NATAL_PROMPT = {
    "uk": "Ти — Аарон, майстер астрології. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ. Структура: 1)☀️Сонячний знак 2)🌙Місячний знак 3)⬆️Аскендент 4)🪐Ключові планети 5)🏠Важливі будинки 6)💫Сильні сторони 7)⚡Виклики 8)🌟Теми життя 9)🔮3-4 поради. Дані: ",
    "ru": "Ты — Аарон, мастер астрологии. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ. Структура: 1)☀️Солнечный знак 2)🌙Лунный знак 3)⬆️Асцендент 4)🪐Ключевые планеты 5)🏠Важные дома 6)💫Сильные стороны 7)⚡Вызовы 8)🌟Темы жизни 9)🔮3-4 совета. Данные: ",
    "en": "You are Aaron, a master astrologer. Reply EXCLUSIVELY IN ENGLISH. Structure: 1)☀️Sun sign 2)🌙Moon sign 3)⬆️Ascendant 4)🪐Key planets 5)🏠Important houses 6)💫Strengths 7)⚡Challenges 8)🌟Life themes 9)🔮3-4 recommendations. Data: ",
    "de": "Du bist Aaron, ein Meister-Astrologe. Antworte AUSSCHLIESSLICH AUF DEUTSCH. Struktur: 1)☀️Sonnenzeichen 2)🌙Mondzeichen 3)⬆️Aszendent 4)🪐Schlüsselplaneten 5)🏠Wichtige Häuser 6)💫Stärken 7)⚡Herausforderungen 8)🌟Lebensthemen 9)🔮3-4 Empfehlungen. Daten: ",
}
COMPAT_PROMPT = {
    "uk": "Ти — Аарон, майстер астрології та нумерології. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ. Структура: 1)🌟Астрологічна сумісність 2)🔢Нумерологічна сумісність 3)❤️Романтика 4)🤝Дружба/справа 5)⚡Точки напруги 6)💫Спільні сильні сторони 7)🔮Прогноз 8)💡3 поради. Відверто, глибоко, з теплотою. Дані: ",
    "ru": "Ты — Аарон, мастер астрологии и нумерологии. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ. Структура: 1)🌟Астрологическая совместимость 2)🔢Нумерологическая совместимость 3)❤️Романтика 4)🤝Дружба/дело 5)⚡Точки напряжения 6)💫Общие сильные стороны 7)🔮Прогноз 8)💡3 совета. Откровенно, глубоко, с теплотой. Данные: ",
    "en": "You are Aaron, master astrologer and numerologist. Reply EXCLUSIVELY IN ENGLISH. Structure: 1)🌟Astrological compatibility 2)🔢Numerological compatibility 3)❤️Romance 4)🤝Friendship/business 5)⚡Tension points 6)💫Shared strengths 7)🔮Forecast 8)💡3 tips. Honest, deep, warm. Data: ",
    "de": "Du bist Aaron, Meister-Astrologe und Numerologe. Antworte AUSSCHLIESSLICH AUF DEUTSCH. Struktur: 1)🌟Astrologische Kompatibilität 2)🔢Numerologische Kompatibilität 3)❤️Romantik 4)🤝Freundschaft/Geschäft 5)⚡Spannungspunkte 6)💫Gemeinsame Stärken 7)🔮Prognose 8)💡3 Tipps. Ehrlich, tiefgründig, warm. Daten: ",
}
HOROSCOPE_PROMPT = {
    "uk": "Ти — Аарон, майстер астрології. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ. Визнач знак зодіаку. Склади гороскоп:\n📅 СЬОГОДНІ ({today}): енергія дня, любов, робота, здоров'я, щасливі числа\n📅 ЗАВТРА ({tomorrow}): енергія дня, любов, робота, здоров'я, порада. Конкретно та практично. Дата народження: ",
    "ru": "Ты — Аарон, мастер астрологии. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ. Определи знак зодиака. Составь гороскоп:\n📅 СЕГОДНЯ ({today}): энергия дня, любовь, работа, здоровье, счастливые числа\n📅 ЗАВТРА ({tomorrow}): энергия дня, любовь, работа, здоровье, совет. Конкретно и практично. Дата рождения: ",
    "en": "You are Aaron, master astrologer. Reply EXCLUSIVELY IN ENGLISH. Determine zodiac sign. Compose horoscope:\n📅 TODAY ({today}): day energy, love, work, health, lucky numbers\n📅 TOMORROW ({tomorrow}): day energy, love, work, health, advice. Specific and practical. Birth date: ",
    "de": "Du bist Aaron, Meister-Astrologe. Antworte AUSSCHLIESSLICH AUF DEUTSCH. Bestimme Tierkreiszeichen. Erstelle Horoskop:\n📅 HEUTE ({today}): Tagesenergie, Liebe, Arbeit, Gesundheit, Glückszahlen\n📅 MORGEN ({tomorrow}): Tagesenergie, Liebe, Arbeit, Gesundheit, Rat. Konkret und praktisch. Geburtsdatum: ",
}

# ─────────────────────────────────────────────
# КЛАВИАТУРЫ
# ─────────────────────────────────────────────
def lang_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🇺🇦 Українська"), KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English"),    KeyboardButton(text="🇩🇪 Deutsch")],
    ], resize_keyboard=True)

def menu_kb(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["menu_palm"]),  KeyboardButton(text=t["menu_num"])],
        [KeyboardButton(text=t["menu_natal"]), KeyboardButton(text=t["menu_compat"])],
        [KeyboardButton(text=t["menu_horoscope"])],
    ], resize_keyboard=True)

def hand_kb(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["left_btn"]), KeyboardButton(text=t["right_btn"])],
        [KeyboardButton(text=t["both_btn"])],
        [KeyboardButton(text=t["back"])],
    ], resize_keyboard=True)

def back_kb(lang):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=TEXTS[lang]["back"])]
    ], resize_keyboard=True)

# ─────────────────────────────────────────────
# УТИЛИТЫ
# ─────────────────────────────────────────────
async def send_long(msg: Message, text: str):
    for i in range(0, len(text), 4000):
        await msg.answer(text[i:i+4000])

def get_state(uid):
    return user_state.get(uid, {"lang": "ru", "step": "lang"})

def show_menu(lang):
    return TEXTS[lang]["choose_menu"]

# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    user_state[uid] = {"step": "lang"}
    await message.answer(
        "🔮 Вітаю / Привет / Hello / Hallo!",
        reply_markup=lang_kb()
    )

# ─────────────────────────────────────────────
# ЕДИНЫЙ ОБРАБОТЧИК ТЕКСТА
# ─────────────────────────────────────────────
@dp.message(F.text)
async def handle_text(message: Message):
    uid  = message.from_user.id
    text = message.text.strip()
    state = get_state(uid)
    step  = state.get("step", "lang")
    lang  = state.get("lang", "ru")
    t     = TEXTS.get(lang, TEXTS["ru"])

    # ── 1. Выбор языка ──────────────────────
    if step == "lang":
        lang_map = {
            "🇺🇦 Українська": "uk",
            "🇷🇺 Русский":    "ru",
            "🇬🇧 English":    "en",
            "🇩🇪 Deutsch":    "de",
        }
        if text in lang_map:
            lang = lang_map[text]
            user_state[uid] = {"lang": lang, "step": "menu"}
            await message.answer(TEXTS[lang]["choose_menu"], reply_markup=menu_kb(lang))
        else:
            await message.answer("🔮", reply_markup=lang_kb())
        return

    # ── 2. Назад в меню ─────────────────────
    if text == t["back"]:
        user_state[uid] = {"lang": lang, "step": "menu"}
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── 3. Главное меню ─────────────────────
    if step == "menu":
        if text == t["menu_palm"]:
            user_state[uid].update({"step": "palm_hand"})
            await message.answer(t["choose_hand"], reply_markup=hand_kb(lang))

        elif text == t["menu_num"]:
            user_state[uid].update({"step": "num_input"})
            await message.answer(t["num_ask"], reply_markup=back_kb(lang))

        elif text == t["menu_natal"]:
            user_state[uid].update({"step": "natal_input"})
            await message.answer(t["natal_ask"], reply_markup=back_kb(lang))

        elif text == t["menu_compat"]:
            user_state[uid].update({"step": "compat_1"})
            await message.answer(t["compat_ask1"], reply_markup=back_kb(lang))

        elif text == t["menu_horoscope"]:
            user_state[uid].update({"step": "horoscope_input"})
            await message.answer(t["horoscope_ask"], reply_markup=back_kb(lang))
        else:
            await message.answer(t["unexpected"], reply_markup=menu_kb(lang))
        return

    # ── 4. Хиромантия — выбор руки ──────────
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

    # ── 5. Нумерология ──────────────────────
    if step == "num_input":
        await message.answer(t["num_analyzing"])
        try:
            resp = model.generate_content(NUMEROLOGY_PROMPT[lang] + text)
            await send_long(message, resp.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── 6. Натальная карта ──────────────────
    if step == "natal_input":
        await message.answer(t["natal_analyzing"])
        try:
            resp = model.generate_content(NATAL_PROMPT[lang] + text)
            await send_long(message, resp.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── 7. Совместимость ────────────────────
    if step == "compat_1":
        user_state[uid].update({"step": "compat_2", "compat_1": text})
        await message.answer(t["compat_ask2"])
        return

    if step == "compat_2":
        person1 = state.get("compat_1", "")
        await message.answer(t["compat_analyzing"])
        try:
            resp = model.generate_content(
                COMPAT_PROMPT[lang] + f"Людина 1 / Человек 1: {person1} | Людина 2 / Человек 2: {text}"
            )
            await send_long(message, resp.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── 8. Гороскоп ─────────────────────────
    if step == "horoscope_input":
        today    = datetime.now().strftime("%d.%m.%Y")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
        await message.answer(t["horoscope_calc"])
        try:
            prompt = HOROSCOPE_PROMPT[lang].format(today=today, tomorrow=tomorrow) + text
            resp = model.generate_content(prompt)
            await send_long(message, resp.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # Непредвиденное
    await message.answer(t["unexpected"], reply_markup=menu_kb(lang))


# ─────────────────────────────────────────────
# ОБРАБОТКА ФОТО
# ─────────────────────────────────────────────
@dp.message(F.photo)
async def handle_photo(message: Message):
    uid   = message.from_user.id
    state = get_state(uid)
    lang  = state.get("lang", "ru")
    step  = state.get("step", "menu")
    t     = TEXTS[lang]

    if step not in ("palm_photo", "palm_left", "palm_right"):
        await message.answer(t["unexpected"], reply_markup=menu_kb(lang))
        return

    # Скачиваем фото
    photo = message.photo[-1]
    file  = await bot.get_file(photo.file_id)
    path  = f"photo_{uid}.jpg"
    await bot.download_file(file.file_path, path)
    with open(path, "rb") as f:
        img = base64.b64encode(f.read()).decode()
    if os.path.exists(path):
        os.remove(path)

    # Ждём левую руку (обе)
    if step == "palm_left":
        user_state[uid].update({"step": "palm_right", "left_img": img})
        await message.answer(t["send_second"])
        return

    # Получили правую — анализируем обе
    if step == "palm_right":
        await message.answer(t["analyzing_both"])
        left_img = state.get("left_img", "")
        try:
            resp = model.generate_content([
                PALM_SYSTEM[lang],
                {"inline_data": {"mime_type": "image/jpeg", "data": left_img}},
                {"inline_data": {"mime_type": "image/jpeg", "data": img}},
                PALM_PROMPTS[lang]["both"]
            ])
            await send_long(message, resp.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["palm_error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # Одна рука
    hand = state.get("hand", "right")
    await message.answer(t["analyzing"])
    try:
        resp = model.generate_content([
            PALM_SYSTEM[lang],
            {"inline_data": {"mime_type": "image/jpeg", "data": img}},
            PALM_PROMPTS[lang][hand]
        ])
        await send_long(message, resp.text)
    except Exception as e:
        logging.error(e)
        await message.answer(t["palm_error"])

    user_state[uid].update({"step": "menu"})
    await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))


# ─────────────────────────────────────────────
async def main():
    print("🔮 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
