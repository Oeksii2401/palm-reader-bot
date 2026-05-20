import asyncio
import logging
import os
import base64
import asyncpg
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime, timedelta
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

user_state = {}
db_pool = None

TEXTS = {
    "uk": {
        "choose_menu":     "🔮 Що бажаєте дізнатися?",
        "menu_palm":       "🖐 Хіромантія",
        "menu_num":        "🔢 Нумерологія",
        "menu_natal":      "⭐ Натальна карта",
        "menu_compat":     "💑 Сумісність",
        "menu_horoscope":  "🌟 Гороскоп",
        "back":            "↩️ Головне меню",
        "exit_btn":        "🚪 Вийти",
        "exit_msg":        "👋 До побачення! Зірки завжди з тобою ✨\n\nНапишіть /start щоб повернутися.",
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
        "choose_menu":     "🔮 Что желаете узнать?",
        "menu_palm":       "🖐 Хиромантия",
        "menu_num":        "🔢 Нумерология",
        "menu_natal":      "⭐ Натальная карта",
        "menu_compat":     "💑 Совместимость",
        "menu_horoscope":  "🌟 Гороскоп",
        "back":            "↩️ Главное меню",
        "exit_btn":        "🚪 Выйти",
        "exit_msg":        "👋 До свидания! Звёзды всегда с тобой ✨\n\nНапишите /start чтобы вернуться.",
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
        "choose_menu":     "🔮 What would you like to explore?",
        "menu_palm":       "🖐 Palmistry",
        "menu_num":        "🔢 Numerology",
        "menu_natal":      "⭐ Natal Chart",
        "menu_compat":     "💑 Compatibility",
        "menu_horoscope":  "🌟 Horoscope",
        "back":            "↩️ Main Menu",
        "exit_btn":        "🚪 Exit",
        "exit_msg":        "👋 Goodbye! The stars are always with you ✨\n\nType /start to return.",
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
        "choose_menu":     "🔮 Was möchten Sie erkunden?",
        "menu_palm":       "🖐 Handlesen",
        "menu_num":        "🔢 Numerologie",
        "menu_natal":      "⭐ Geburtshoroskop",
        "menu_compat":     "💑 Partnerschaft",
        "menu_horoscope":  "🌟 Horoskop",
        "back":            "↩️ Hauptmenü",
        "exit_btn":        "🚪 Beenden",
        "exit_msg":        "👋 Auf Wiedersehen! Die Sterne sind immer bei dir ✨\n\nSchreiben Sie /start um zurückzukehren.",
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

PALM_SYSTEM = {
    "uk": "Ти — Аарон, майстер-хіромант із 25-річним досвідом. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ. СТРУКТУРА: 1)Тип руки та загальна енергетика 2)Лінія Життя 3)Лінія Серця 4)Лінія Голови 5)Лінія Долі 6)Горби 7)Пальці 8)Загальний висновок 9)3 конкретні поради. Стиль: глибокий, серйозний, мудрий наставник з теплою усмішкою. Використовуй емодзі для структури.",
    "ru": "Ты — Аарон, мастер-хиромант с 25-летним опытом. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ. СТРУКТУРА: 1)Тип руки и общая энергетика 2)Линия Жизни 3)Линия Сердца 4)Линия Головы 5)Линия Судьбы 6)Холмы 7)Пальцы 8)Общий вывод 9)3 конкретных совета. Стиль: глубокий, серьёзный, мудрый наставник с доброй улыбкой. Используй эмодзи для структуры.",
    "en": "You are Aaron, a master palmist with 25 years of experience. Reply EXCLUSIVELY IN ENGLISH. STRUCTURE: 1)Hand type & energy 2)Life Line 3)Heart Line 4)Head Line 5)Fate Line 6)Mounts 7)Fingers 8)Overall conclusion 9)3 specific pieces of advice. Style: deep, serious, wise mentor with a warm smile. Use emojis for structure.",
    "de": "Du bist Aaron, ein Meister-Handleser mit 25 Jahren Erfahrung. Antworte AUSSCHLIESSLICH AUF DEUTSCH. STRUKTUR: 1)Handtyp & Energie 2)Lebenslinie 3)Herzlinie 4)Kopflinie 5)Schicksalslinie 6)Hügel 7)Finger 8)Gesamtschluss 9)3 konkrete Ratschläge. Stil: tiefgründig, ernsthaft, weiser Mentor mit warmem Lächeln. Verwende Emojis.",
}

PALM_PROMPTS = {
    "uk": {
        "left":  "ЛІВА (пасивна) рука — природжений потенціал, карма, спадковість. Що дано від народження?",
        "right": "ПРАВА (активна) рука — реалізація, теперішнє, майбутні можливості. Що людина зробила зі своїм потенціалом?",
        "both":  "Перше фото ЛІВА рука, друге ПРАВА. Порівняй обидві: де реалізовано потенціал, де є резерви?",
    },
    "ru": {
        "left":  "ЛЕВАЯ (пассивная) рука — врождённый потенциал, карма, наследственность. Что дано от природы?",
        "right": "ПРАВАЯ (активная) рука — реализация, настоящее, будущие возможности. Что человек сделал со своим потенциалом?",
        "both":  "Первое фото ЛЕВАЯ рука, второе ПРАВАЯ. Сравни обе: где реализован потенциал, где есть резервы?",
    },
    "en": {
        "left":  "LEFT (passive) hand — innate potential, karma, heredity. What was given by nature?",
        "right": "RIGHT (active) hand — realization, present, future opportunities. What has this person done with their potential?",
        "both":  "First photo LEFT hand, second RIGHT. Compare both: where is potential fulfilled, where are reserves?",
    },
    "de": {
        "left":  "LINKE (passive) Hand — angeborenes Potenzial, Karma, Erbschaft. Was wurde von der Natur gegeben?",
        "right": "RECHTE (aktive) Hand — Realisierung, Gegenwart, Zukunft. Was hat die Person mit ihrem Potenzial gemacht?",
        "both":  "Erstes Foto LINKE Hand, zweites RECHTE. Vergleiche beide: Wo ist Potenzial erfüllt, wo gibt es Reserven?",
    },
}

NUMEROLOGY_PROMPT = {
    "uk": "Ти — Аарон, майстер нумерології. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ. Розрахуй та поясни: 1)🔢Число Життєвого Шляху (покажи розрахунок) 2)💫Число Долі (за таблицею Піфагора) 3)🌟Число Душі (голосні) 4)🎭Число Особистості (приголосні) 5)📅Число Дня Народження 6)🔮Особисте Число Поточного Року. Глибоке тлумачення кожного числа. 3 конкретні поради в кінці. Дані: ",
    "ru": "Ты — Аарон, мастер нумерологии. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ. Рассчитай и объясни: 1)🔢Число Жизненного Пути (покажи расчёт) 2)💫Число Судьбы (по таблице Пифагора) 3)🌟Число Души (гласные) 4)🎭Число Личности (согласные) 5)📅Число Дня Рождения 6)🔮Личное Число Текущего Года. Глубокое толкование каждого числа. 3 конкретных совета в конце. Данные: ",
    "en": "You are Aaron, a master numerologist. Reply EXCLUSIVELY IN ENGLISH. Calculate and explain: 1)🔢Life Path Number (show calculation) 2)💫Destiny Number (Pythagorean table) 3)🌟Soul Number (vowels) 4)🎭Personality Number (consonants) 5)📅Birth Day Number 6)🔮Personal Year Number. Deep interpretation of each number. 3 specific recommendations at end. Data: ",
    "de": "Du bist Aaron, ein Meister-Numerologe. Antworte AUSSCHLIESSLICH AUF DEUTSCH. Berechne und erkläre: 1)🔢Lebenspfadzahl (zeige Berechnung) 2)💫Schicksalszahl (Pythagoras-Tabelle) 3)🌟Seelenzahl (Vokale) 4)🎭Persönlichkeitszahl (Konsonanten) 5)📅Geburtstagszahl 6)🔮Persönliche Jahreszahl. Tiefe Interpretation jeder Zahl. 3 konkrete Empfehlungen am Ende. Daten: ",
}

NATAL_PROMPT = {
    "uk": "Ти — Аарон, майстер астрології. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ. Структура: 1)☀️Сонячний знак — ядро особистості 2)🌙Місячний знак — емоційна природа 3)⬆️Аскендент — як сприймають оточуючі 4)🪐Ключові планети та їх положення 5)🏠Найважливіші будинки 6)💫Сильні сторони карти 7)⚡Виклики та уроки 8)🌟Головні теми життя 9)🔮3-4 конкретні поради. Стиль: глибокий, мудрий, серйозний. Дані: ",
    "ru": "Ты — Аарон, мастер астрологии. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ. Структура: 1)☀️Солнечный знак — ядро личности 2)🌙Лунный знак — эмоциональная природа 3)⬆️Асцендент — как воспринимают окружающие 4)🪐Ключевые планеты и их положения 5)🏠Важнейшие дома 6)💫Сильные стороны карты 7)⚡Вызовы и уроки 8)🌟Главные темы жизни 9)🔮3-4 конкретных совета. Стиль: глубокий, мудрый, серьёзный. Данные: ",
    "en": "You are Aaron, a master astrologer. Reply EXCLUSIVELY IN ENGLISH. Structure: 1)☀️Sun sign — personality core 2)🌙Moon sign — emotional nature 3)⬆️Ascendant — how others perceive you 4)🪐Key planets & positions 5)🏠Most important houses 6)💫Chart strengths 7)⚡Challenges & lessons 8)🌟Main life themes 9)🔮3-4 specific recommendations. Style: deep, wise, serious. Data: ",
    "de": "Du bist Aaron, ein Meister-Astrologe. Antworte AUSSCHLIESSLICH AUF DEUTSCH. Struktur: 1)☀️Sonnenzeichen — Persönlichkeitskern 2)🌙Mondzeichen — emotionale Natur 3)⬆️Aszendent — wie andere Sie wahrnehmen 4)🪐Schlüsselplaneten & Positionen 5)🏠Wichtigste Häuser 6)💫Kartenstärken 7)⚡Herausforderungen & Lektionen 8)🌟Hauptlebensthemen 9)🔮3-4 konkrete Empfehlungen. Stil: tiefgründig, weise, ernsthaft. Daten: ",
}

COMPAT_PROMPT = {
    "uk": "Ти — Аарон, майстер астрології та нумерології. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ. Структура: 1)🌟Астрологічна сумісність (знаки зодіаку) 2)🔢Нумерологічна сумісність (числа життєвого шляху) 3)❤️Романтика та пристрасть 4)🤝Дружба та спільна справа 5)⚡Точки напруги та як їх долати 6)💫Спільні сильні сторони 7)🔮Загальний прогноз 8)💡3 практичні поради. Відверто, глибоко, з теплотою. Дані: ",
    "ru": "Ты — Аарон, мастер астрологии и нумерологии. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ. Структура: 1)🌟Астрологическая совместимость (знаки зодиака) 2)🔢Нумерологическая совместимость (числа жизненного пути) 3)❤️Романтика и страсть 4)🤝Дружба и общее дело 5)⚡Точки напряжения и как их преодолевать 6)💫Общие сильные стороны 7)🔮Общий прогноз 8)💡3 практических совета. Откровенно, глубоко, с теплотой. Данные: ",
    "en": "You are Aaron, master astrologer and numerologist. Reply EXCLUSIVELY IN ENGLISH. Structure: 1)🌟Astrological compatibility 2)🔢Numerological compatibility 3)❤️Romance & passion 4)🤝Friendship & business 5)⚡Tension points & how to overcome them 6)💫Shared strengths 7)🔮Overall forecast 8)💡3 practical tips. Honest, deep, warm. Data: ",
    "de": "Du bist Aaron, Meister-Astrologe und Numerologe. Antworte AUSSCHLIESSLICH AUF DEUTSCH. Struktur: 1)🌟Astrologische Kompatibilität 2)🔢Numerologische Kompatibilität 3)❤️Romantik & Leidenschaft 4)🤝Freundschaft & Geschäft 5)⚡Spannungspunkte & Lösungen 6)💫Gemeinsame Stärken 7)🔮Gesamtprognose 8)💡3 praktische Tipps. Ehrlich, tiefgründig, warm. Daten: ",
}

HOROSCOPE_PROMPT = {
    "uk": """Ти — Аарон, майстер астрології. Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ.
ВАЖЛИВО про граничні дати: якщо дата народження припадає на 19-20 лютого, 20-21 березня, 19-20 квітня, 20-21 травня, 20-21 червня, 22-23 липня, 22-23 серпня, 22-23 вересня, 22-23 жовтня, 21-22 листопада, 21-22 грудня, 19-20 січня — поясни що людина знаходиться на куспіді (межі двох знаків) і розкажи про вплив обох знаків.
Визнач знак зодіаку та склади гороскоп:
📅 СЬОГОДНІ ({today}):
- Загальна енергія дня
- Любов і стосунки  
- Робота і фінанси
- Здоров'я
- Щасливі числа та колір

📅 ЗАВТРА ({tomorrow}):
- Загальна енергія дня
- Любов і стосунки
- Робота і фінанси
- Здоров'я
- Головна порада дня

Конкретно, практично, надихаючо. Дата народження: """,

    "ru": """Ты — Аарон, мастер астрологии. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ.
ВАЖНО о граничных датах: если дата рождения приходится на 19-20 февраля, 20-21 марта, 19-20 апреля, 20-21 мая, 20-21 июня, 22-23 июля, 22-23 августа, 22-23 сентября, 22-23 октября, 21-22 ноября, 21-22 декабря, 19-20 января — объясни что человек находится на куспиде (границе двух знаков) и расскажи о влиянии обоих знаков.
Определи знак зодиака и составь гороскоп:
📅 СЕГОДНЯ ({today}):
- Общая энергия дня
- Любовь и отношения
- Работа и финансы
- Здоровье
- Счастливые числа и цвет

📅 ЗАВТРА ({tomorrow}):
- Общая энергия дня
- Любовь и отношения
- Работа и финансы
- Здоровье
- Главный совет дня

Конкретно, практично, вдохновляюще. Дата рождения: """,

    "en": """You are Aaron, master astrologer. Reply EXCLUSIVELY IN ENGLISH.
IMPORTANT about cusp dates: if the birth date falls on Feb 19-20, Mar 20-21, Apr 19-20, May 20-21, Jun 20-21, Jul 22-23, Aug 22-23, Sep 22-23, Oct 22-23, Nov 21-22, Dec 21-22, Jan 19-20 — explain the person is on a cusp (border of two signs) and describe the influence of both signs.
Determine zodiac sign and compose horoscope:
📅 TODAY ({today}):
- General energy of the day
- Love & relationships
- Work & finances
- Health
- Lucky numbers & color

📅 TOMORROW ({tomorrow}):
- General energy of the day
- Love & relationships
- Work & finances
- Health
- Main advice of the day

Specific, practical, inspiring. Birth date: """,

    "de": """Du bist Aaron, Meister-Astrologe. Antworte AUSSCHLIESSLICH AUF DEUTSCH.
WICHTIG bei Grenzdaten: Falls das Geburtsdatum auf den 19.-20. Feb, 20.-21. März, 19.-20. Apr, 20.-21. Mai, 20.-21. Jun, 22.-23. Jul, 22.-23. Aug, 22.-23. Sep, 22.-23. Okt, 21.-22. Nov, 21.-22. Dez, 19.-20. Jan fällt — erkläre dass die Person auf einem Kusp (Grenze zweier Zeichen) ist und beschreibe den Einfluss beider Zeichen.
Bestimme Tierkreiszeichen und erstelle Horoskop:
📅 HEUTE ({today}):
- Allgemeine Tagesenergie
- Liebe & Beziehungen
- Arbeit & Finanzen
- Gesundheit
- Glückszahlen & Farbe

📅 MORGEN ({tomorrow}):
- Allgemeine Tagesenergie
- Liebe & Beziehungen
- Arbeit & Finanzen
- Gesundheit
- Hauptrat des Tages

Konkret, praktisch, inspirierend. Geburtsdatum: """,
}

# ─────────────────────────────────────────────
# БАЗА ДАННЫХ
# ─────────────────────────────────────────────
async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id       BIGINT PRIMARY KEY,
                lang          TEXT DEFAULT 'ru',
                free_uses     INTEGER DEFAULT 0,
                is_subscribed BOOLEAN DEFAULT FALSE,
                sub_until     TIMESTAMP DEFAULT NULL,
                ref_code      TEXT DEFAULT NULL,
                referred_by   BIGINT DEFAULT NULL,
                created_at    TIMESTAMP DEFAULT NOW()
            )
        ''')
    logging.info("✅ БД инициализирована")

async def get_or_create_user(uid: int):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            'SELECT * FROM users WHERE user_id = $1', uid
        )
        if not user:
            await conn.execute(
                'INSERT INTO users (user_id) VALUES ($1)', uid
            )
            user = await conn.fetchrow(
                'SELECT * FROM users WHERE user_id = $1', uid
            )
        return user

async def save_lang(uid: int, lang: str):
    async with db_pool.acquire() as conn:
        await conn.execute(
            'UPDATE users SET lang = $1 WHERE user_id = $2', lang, uid
        )

async def increment_uses(uid: int):
    async with db_pool.acquire() as conn:
        await conn.execute(
            'UPDATE users SET free_uses = free_uses + 1 WHERE user_id = $1', uid
        )

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
        [KeyboardButton(text=t["menu_palm"]),      KeyboardButton(text=t["menu_num"])],
        [KeyboardButton(text=t["menu_natal"]),     KeyboardButton(text=t["menu_compat"])],
        [KeyboardButton(text=t["menu_horoscope"])],
        [KeyboardButton(text=t["exit_btn"])],
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

# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    # Создаём или загружаем пользователя из БД
    user = await get_or_create_user(uid)
    # Восстанавливаем язык из БД если он уже был выбран
    saved_lang = user['lang'] if user else 'ru'
    user_state[uid] = {"step": "lang", "lang": saved_lang}
    await message.answer(
        "🔮 Вітаю / Привет / Hello / Hallo!",
        reply_markup=lang_kb()
    )

# ─────────────────────────────────────────────
# ЕДИНЫЙ ОБРАБОТЧИК ТЕКСТА
# ─────────────────────────────────────────────
@dp.message(F.text)
async def handle_text(message: Message):
    uid   = message.from_user.id
    text  = message.text.strip()
    state = get_state(uid)
    step  = state.get("step", "lang")
    lang  = state.get("lang", "ru")
    t     = TEXTS.get(lang, TEXTS["ru"])

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
            user_state[uid] = {"lang": lang, "step": "menu"}
            # Сохраняем язык в БД
            await get_or_create_user(uid)
            await save_lang(uid, lang)
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

    # ── Нумерология ─────────────────────────
    if step == "num_input":
        await message.answer(t["num_analyzing"])
        try:
            resp = model.generate_content(NUMEROLOGY_PROMPT[lang] + text)
            await send_long(message, resp.text)
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── Натальная карта ─────────────────────
    if step == "natal_input":
        await message.answer(t["natal_analyzing"])
        try:
            resp = model.generate_content(NATAL_PROMPT[lang] + text)
            await send_long(message, resp.text)
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── Совместимость ───────────────────────
    if step == "compat_1":
        user_state[uid].update({"step": "compat_2", "compat_1": text})
        await message.answer(t["compat_ask2"])
        return

    if step == "compat_2":
        person1 = state.get("compat_1", "")
        await message.answer(t["compat_analyzing"])
        try:
            resp = model.generate_content(
                COMPAT_PROMPT[lang] +
                f"Людина 1 / Человек 1 / Person 1: {person1} | "
                f"Людина 2 / Человек 2 / Person 2: {text}"
            )
            await send_long(message, resp.text)
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    # ── Гороскоп ────────────────────────────
    if step == "horoscope_input":
        today    = datetime.now().strftime("%d.%m.%Y")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
        await message.answer(t["horoscope_calc"])
        try:
            prompt = HOROSCOPE_PROMPT[lang].format(today=today, tomorrow=tomorrow) + text
            resp = model.generate_content(prompt)
            await send_long(message, resp.text)
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

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

    photo = message.photo[-1]
    file  = await bot.get_file(photo.file_id)
    path  = f"photo_{uid}.jpg"
    await bot.download_file(file.file_path, path)
    with open(path, "rb") as f:
        img = base64.b64encode(f.read()).decode()
    if os.path.exists(path):
        os.remove(path)

    if step == "palm_left":
        user_state[uid].update({"step": "palm_right", "left_img": img})
        await message.answer(t["send_second"])
        return

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
            await increment_uses(uid)
        except Exception as e:
            logging.error(e)
            await message.answer(t["palm_error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))
        return

    hand = state.get("hand", "right")
    await message.answer(t["analyzing"])
    try:
        resp = model.generate_content([
            PALM_SYSTEM[lang],
            {"inline_data": {"mime_type": "image/jpeg", "data": img}},
            PALM_PROMPTS[lang][hand]
        ])
        await send_long(message, resp.text)
        await increment_uses(uid)
    except Exception as e:
        logging.error(e)
        await message.answer(t["palm_error"])

    user_state[uid].update({"step": "menu"})
    await message.answer(t["choose_menu"], reply_markup=menu_kb(lang))


# ─────────────────────────────────────────────
async def main():
    await init_db()
    print("🔮 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
