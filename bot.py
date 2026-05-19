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

user_state = {}

# ─────────────────────────────────────────────
# ТЕКСТЫ ИНТЕРФЕЙСА
# ─────────────────────────────────────────────
TEXTS = {
    "uk": {
        "choose_menu": "🔮 Що бажаєте дізнатися?",
        "menu_palm":   "🖐 Хіромантія",
        "menu_num":    "🔢 Нумерологія",
        "menu_natal":  "⭐ Натальна карта",
        "menu_compat": "💑 Сумісність",
        "menu_horoscope": "🌟 Гороскоп",
        "back":        "↩️ Головне меню",
        # Хіромантія
        "choose_hand": "🖐 Яку руку гадаємо?\n\n• Права — активна (теперішнє і майбутнє)\n• Ліва — пасивна (потенціал і минуле)",
        "left_btn":    "🤚 Ліва рука",
        "right_btn":   "✋ Права рука",
        "both_btn":    "🙌 Обидві руки",
        "send_left":   "📸 Надішліть фото ЛІВОЇ руки (долоня вгору, гарне освітлення)",
        "send_right":  "📸 Надішліть фото ПРАВОЇ руки (долоня вгору, гарне освітлення)",
        "send_second": "📸 Чудово! Тепер надішліть фото ПРАВОЇ руки",
        "analyzing":   "✨ Читаю лінії долі... Зачекайте.",
        "analyzing_both": "✨ Порівнюю обидві долоні...",
        "palm_error":  "😔 Не вдалося розібрати фото. Спробуйте інше — пряме освітлення, долоня чітко видна.",
        # Нумерологія
        "num_ask_name": "🔢 Нумерологія\n\nВведіть ваше ПОВНЕ ім'я та дату народження через кому:\n\nПриклад:\nІван Петренко Олексійович, 15.03.1990",
        "num_analyzing": "🔢 Розраховую ваш нумерологічний портрет...",
        # Натальна карта
        "natal_ask": "⭐ Натальна карта\n\nВведіть дату, час та місце народження:\n\nПриклад:\n15.03.1990, 14:30, Київ, Україна\n\n(Якщо час невідомий — напишіть 12:00)",
        "natal_analyzing": "⭐ Будую вашу натальну карту...",
        # Сумісність
        "compat_ask1": "💑 Сумісність\n\nВведіть дані ПЕРШОЇ людини (ім'я та дата народження):\n\nПриклад:\nМарія, 15.03.1990",
        "compat_ask2": "💑 Чудово! Тепер введіть дані ДРУГОЇ людини:\n\nПриклад:\nОлексій, 22.07.1988",
        "compat_analyzing": "💑 Аналізую сумісність...",
        # Гороскоп
        "horoscope_ask": "🌟 Гороскоп\n\nВведіть вашу дату народження:\n\nПриклад:\n15.03.1990",
        "horoscope_analyzing": "🌟 Складаю ваш гороскоп на сьогодні та завтра...",
        "error": "😔 Щось пішло не так. Спробуйте ще раз.",
    },
    "ru": {
        "choose_menu": "🔮 Что желаете узнать?",
        "menu_palm":   "🖐 Хиромантия",
        "menu_num":    "🔢 Нумерология",
        "menu_natal":  "⭐ Натальная карта",
        "menu_compat": "💑 Совместимость",
        "menu_horoscope": "🌟 Гороскоп",
        "back":        "↩️ Главное меню",
        "choose_hand": "🖐 Какую руку читаем?\n\n• Правая — активная (настоящее и будущее)\n• Левая — пассивная (потенциал и прошлое)",
        "left_btn":    "🤚 Левая рука",
        "right_btn":   "✋ Правая рука",
        "both_btn":    "🙌 Обе руки",
        "send_left":   "📸 Пришлите фото ЛЕВОЙ руки (ладонь вверх, хорошее освещение)",
        "send_right":  "📸 Пришлите фото ПРАВОЙ руки (ладонь вверх, хорошее освещение)",
        "send_second": "📸 Отлично! Теперь пришлите фото ПРАВОЙ руки",
        "analyzing":   "✨ Читаю линии судьбы... Подождите.",
        "analyzing_both": "✨ Сравниваю обе ладони...",
        "palm_error":  "😔 Не удалось разобрать фото. Попробуйте другое — прямое освещение, ладонь чётко видна.",
        "num_ask_name": "🔢 Нумерология\n\nВведите ваше ПОЛНОЕ имя и дату рождения через запятую:\n\nПример:\nИван Петров Алексеевич, 15.03.1990",
        "num_analyzing": "🔢 Рассчитываю ваш нумерологический портрет...",
        "natal_ask": "⭐ Натальная карта\n\nВведите дату, время и место рождения:\n\nПример:\n15.03.1990, 14:30, Киев, Украина\n\n(Если время неизвестно — напишите 12:00)",
        "natal_analyzing": "⭐ Строю вашу натальную карту...",
        "compat_ask1": "💑 Совместимость\n\nВведите данные ПЕРВОГО человека (имя и дата рождения):\n\nПример:\nМария, 15.03.1990",
        "compat_ask2": "💑 Отлично! Теперь введите данные ВТОРОГО человека:\n\nПример:\nАлексей, 22.07.1988",
        "compat_analyzing": "💑 Анализирую совместимость...",
        "horoscope_ask": "🌟 Гороскоп\n\nВведите вашу дату рождения:\n\nПример:\n15.03.1990",
        "horoscope_analyzing": "🌟 Составляю ваш гороскоп на сегодня и завтра...",
        "error": "😔 Что-то пошло не так. Попробуйте ещё раз.",
    },
    "en": {
        "choose_menu": "🔮 What would you like to explore?",
        "menu_palm":   "🖐 Palmistry",
        "menu_num":    "🔢 Numerology",
        "menu_natal":  "⭐ Natal Chart",
        "menu_compat": "💑 Compatibility",
        "menu_horoscope": "🌟 Horoscope",
        "back":        "↩️ Main Menu",
        "choose_hand": "🖐 Which hand shall we read?\n\n• Right hand — active (present & future)\n• Left hand — passive (potential & past)",
        "left_btn":    "🤚 Left hand",
        "right_btn":   "✋ Right hand",
        "both_btn":    "🙌 Both hands",
        "send_left":   "📸 Send a photo of your LEFT hand (palm facing up, good lighting)",
        "send_right":  "📸 Send a photo of your RIGHT hand (palm facing up, good lighting)",
        "send_second": "📸 Great! Now send a photo of your RIGHT hand",
        "analyzing":   "✨ Reading the lines of fate... Please wait.",
        "analyzing_both": "✨ Comparing both palms...",
        "palm_error":  "😔 Couldn't analyze the photo. Please try again — direct lighting, palm clearly visible.",
        "num_ask_name": "🔢 Numerology\n\nEnter your FULL name and date of birth separated by a comma:\n\nExample:\nJohn Alexander Smith, 15.03.1990",
        "num_analyzing": "🔢 Calculating your numerological portrait...",
        "natal_ask": "⭐ Natal Chart\n\nEnter your date, time and place of birth:\n\nExample:\n15.03.1990, 14:30, London, UK\n\n(If time is unknown — write 12:00)",
        "natal_analyzing": "⭐ Building your natal chart...",
        "compat_ask1": "💑 Compatibility\n\nEnter the FIRST person's details (name and date of birth):\n\nExample:\nMaria, 15.03.1990",
        "compat_ask2": "💑 Great! Now enter the SECOND person's details:\n\nExample:\nAlex, 22.07.1988",
        "compat_analyzing": "💑 Analyzing compatibility...",
        "horoscope_ask": "🌟 Horoscope\n\nEnter your date of birth:\n\nExample:\n15.03.1990",
        "horoscope_analyzing": "🌟 Preparing your horoscope for today and tomorrow...",
        "error": "😔 Something went wrong. Please try again.",
    },
    "de": {
        "choose_menu": "🔮 Was möchten Sie erkunden?",
        "menu_palm":   "🖐 Handlesen",
        "menu_num":    "🔢 Numerologie",
        "menu_natal":  "⭐ Geburtshoroskop",
        "menu_compat": "💑 Partnerschaft",
        "menu_horoscope": "🌟 Horoskop",
        "back":        "↩️ Hauptmenü",
        "choose_hand": "🖐 Welche Hand lesen wir?\n\n• Rechte Hand — aktiv (Gegenwart & Zukunft)\n• Linke Hand — passiv (Potenzial & Vergangenheit)",
        "left_btn":    "🤚 Linke Hand",
        "right_btn":   "✋ Rechte Hand",
        "both_btn":    "🙌 Beide Hände",
        "send_left":   "📸 Senden Sie ein Foto Ihrer LINKEN Hand (Handfläche nach oben, gute Beleuchtung)",
        "send_right":  "📸 Senden Sie ein Foto Ihrer RECHTEN Hand (Handfläche nach oben, gute Beleuchtung)",
        "send_second": "📸 Wunderbar! Jetzt senden Sie ein Foto Ihrer RECHTEN Hand",
        "analyzing":   "✨ Lese die Schicksalslinien... Bitte warten.",
        "analyzing_both": "✨ Vergleiche beide Handflächen...",
        "palm_error":  "😔 Foto konnte nicht analysiert werden. Bitte erneut versuchen — gute Beleuchtung, Handfläche klar sichtbar.",
        "num_ask_name": "🔢 Numerologie\n\nGeben Sie Ihren VOLLSTÄNDIGEN Namen und Ihr Geburtsdatum ein:\n\nBeispiel:\nHans Friedrich Müller, 15.03.1990",
        "num_analyzing": "🔢 Berechne Ihr numerologisches Porträt...",
        "natal_ask": "⭐ Geburtshoroskop\n\nGeben Sie Datum, Uhrzeit und Geburtsort ein:\n\nBeispiel:\n15.03.1990, 14:30, Berlin, Deutschland\n\n(Falls Uhrzeit unbekannt — schreiben Sie 12:00)",
        "natal_analyzing": "⭐ Erstelle Ihr Geburtshoroskop...",
        "compat_ask1": "💑 Partnerschaft\n\nGeben Sie die Daten der ERSTEN Person ein:\n\nBeispiel:\nMaria, 15.03.1990",
        "compat_ask2": "💑 Gut! Jetzt geben Sie die Daten der ZWEITEN Person ein:\n\nBeispiel:\nAlex, 22.07.1988",
        "compat_analyzing": "💑 Analysiere die Kompatibilität...",
        "horoscope_ask": "🌟 Horoskop\n\nGeben Sie Ihr Geburtsdatum ein:\n\nBeispiel:\n15.03.1990",
        "horoscope_analyzing": "🌟 Erstelle Ihr Horoskop für heute und morgen...",
        "error": "😔 Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.",
    }
}

# ─────────────────────────────────────────────
# ПРОМТЫ
# ─────────────────────────────────────────────
PALM_SYSTEM = {
    "uk": """Ти — Аарон, майстер-хіромант із 25-річним досвідом. Ти навчався у найкращих хірологів світу та поєднуєш класичну індійську та європейську традиції хіромантії.

СТИЛЬ: Теплий, поважний, глибокий. Говориш як мудрий наставник — серйозно, але з доброю усмішкою. Легкий гумор доречний, але не перетворюй читання на жарт. Людина прийшла за справжньою відповіддю.

СТРУКТУРА ВІДПОВІДІ:
1. Перше враження від долоні (тип руки, енергетика)
2. Лінія Життя — докладно
3. Лінія Серця — докладно
4. Лінія Голови — докладно
5. Лінія Долі (якщо видно)
6. Горби та їх значення
7. Пальці та їх характеристики
8. Загальний висновок про характер і долю
9. 2-3 конкретні поради для цієї людини

Відповідай ВИКЛЮЧНО УКРАЇНСЬКОЮ мовою. Використовуй емодзі для структури.""",

    "ru": """Ты — Аарон, мастер-хиромант с 25-летним опытом. Ты обучался у лучших хирологов мира и соединяешь классическую индийскую и европейскую традиции хиромантии.

СТИЛЬ: Тёплый, уважительный, глубокий. Говоришь как мудрый наставник — серьёзно, но с доброй улыбкой. Лёгкий юмор уместен, но не превращай чтение в шутку. Человек пришёл за настоящим ответом.

СТРУКТУРА ОТВЕТА:
1. Первое впечатление от ладони (тип руки, энергетика)
2. Линия Жизни — подробно
3. Линия Сердца — подробно
4. Линия Головы — подробно
5. Линия Судьбы (если видна)
6. Холмы и их значение
7. Пальцы и их характеристики
8. Общий вывод о характере и судьбе
9. 2-3 конкретных совета для этого человека

Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ языке. Используй эмодзи для структуры.""",

    "en": """You are Aaron, a master palmist with 25 years of experience. You studied under the world's finest chirologists and blend classical Indian and European palmistry traditions.

STYLE: Warm, respectful, deep. Speak like a wise mentor — seriously but with a kind smile. Light humor is welcome, but don't turn the reading into a joke. The person came for a real answer.

RESPONSE STRUCTURE:
1. First impression of the palm (hand type, energy)
2. Life Line — in detail
3. Heart Line — in detail
4. Head Line — in detail
5. Fate Line (if visible)
6. Mounts and their meaning
7. Fingers and their characteristics
8. Overall conclusion about character and destiny
9. 2-3 specific pieces of advice for this person

Reply EXCLUSIVELY IN ENGLISH. Use emojis for structure.""",

    "de": """Du bist Aaron, ein Meister-Handleser mit 25 Jahren Erfahrung. Du hast bei den besten Chirologen der Welt studiert und verbindest klassische indische und europäische Handlese-Traditionen.

STIL: Warm, respektvoll, tiefgründig. Sprich wie ein weiser Mentor — ernsthaft, aber mit einem freundlichen Lächeln. Leichter Humor ist willkommen, aber mache keine Witze. Die Person kam für eine echte Antwort.

ANTWORTSTRUKTUR:
1. Erster Eindruck der Handfläche (Handtyp, Energie)
2. Lebenslinie — ausführlich
3. Herzlinie — ausführlich
4. Kopflinie — ausführlich
5. Schicksalslinie (falls sichtbar)
6. Hügel und ihre Bedeutung
7. Finger und ihre Charakteristiken
8. Gesamtschlussfolgerung über Charakter und Schicksal
9. 2-3 konkrete Ratschläge für diese Person

Antworte AUSSCHLIESSLICH AUF DEUTSCH. Verwende Emojis für die Struktur."""
}

PALM_PROMPTS = {
    "uk": {
        "left": "Це ЛІВА (пасивна) рука. Аналізуй природжений потенціал, таланти від народження, карму та спадковість. Що людині дано від природи?",
        "right": "Це ПРАВА (активна) рука. Аналізуй реалізований потенціал, теперішнє життя, досягнення та майбутні можливості. Що людина зробила зі своїм даром?",
        "both": "Перше фото — ЛІВА рука (потенціал від народження), друге — ПРАВА рука (реалізація). Порівняй обидві: де людина реалізувала свій потенціал, а де ще є резерви?"
    },
    "ru": {
        "left": "Это ЛЕВАЯ (пассивная) рука. Анализируй врождённый потенциал, таланты от рождения, карму и наследственность. Что дано человеку от природы?",
        "right": "Это ПРАВАЯ (активная) рука. Анализируй реализованный потенциал, нынешнюю жизнь, достижения и будущие возможности. Что человек сделал со своим даром?",
        "both": "Первое фото — ЛЕВАЯ рука (потенциал от рождения), второе — ПРАВАЯ рука (реализация). Сравни обе: где человек реализовал свой потенциал, а где ещё есть резервы?"
    },
    "en": {
        "left": "This is the LEFT (passive) hand. Analyze innate potential, talents from birth, karma and heredity. What has nature given this person?",
        "right": "This is the RIGHT (active) hand. Analyze realized potential, current life, achievements and future opportunities. What has this person done with their gift?",
        "both": "First photo — LEFT hand (potential from birth), second — RIGHT hand (realization). Compare both: where has the person fulfilled their potential, and where are there still reserves?"
    },
    "de": {
        "left": "Dies ist die LINKE (passive) Hand. Analysiere angeborenes Potenzial, Talente von Geburt, Karma und Erbschaft. Was hat die Natur dieser Person gegeben?",
        "right": "Dies ist die RECHTE (aktive) Hand. Analysiere realisiertes Potenzial, aktuelles Leben, Errungenschaften und zukünftige Möglichkeiten. Was hat diese Person aus ihrer Gabe gemacht?",
        "both": "Erstes Foto — LINKE Hand (Potenzial von Geburt), zweites — RECHTE Hand (Realisierung). Vergleiche beide: Wo hat die Person ihr Potenzial verwirklicht, und wo gibt es noch Reserven?"
    }
}

NUMEROLOGY_PROMPT = {
    "uk": """Ти — Аарон, майстер нумерології з 25-річним досвідом. Аналізуй ВИКЛЮЧНО УКРАЇНСЬКОЮ.

РОЗРАХУЙ І ПОЯСНИ:
1. 🔢 Число Життєвого Шляху (сума цифр дати народження)
2. 💫 Число Долі (сума цифр повного імені за таблицею Піфагора)
3. 🌟 Число Душі (голосні літери імені)
4. 🎭 Число Особистості (приголосні літери)
5. 📅 Число Народження (день народження)
6. 🔮 Особисте Число Року (поточний рік)

Покажи всі розрахунки крок за кроком. Дай глибоке тлумачення кожного числа. Стиль: серйозний, глибокий, але теплий. В кінці — 3 конкретні рекомендації.""",

    "ru": """Ты — Аарон, мастер нумерологии с 25-летним опытом. Анализируй ИСКЛЮЧИТЕЛЬНО НА РУССКОМ.

РАССЧИТАЙ И ОБЪЯСНИ:
1. 🔢 Число Жизненного Пути (сумма цифр даты рождения)
2. 💫 Число Судьбы (сумма цифр полного имени по таблице Пифагора)
3. 🌟 Число Души (гласные буквы имени)
4. 🎭 Число Личности (согласные буквы)
5. 📅 Число Рождения (день рождения)
6. 🔮 Личное Число Года (текущий год)

Покажи все расчёты шаг за шагом. Дай глубокое толкование каждого числа. Стиль: серьёзный, глубокий, но тёплый. В конце — 3 конкретные рекомендации.""",

    "en": """You are Aaron, a master numerologist with 25 years of experience. Analyze EXCLUSIVELY IN ENGLISH.

CALCULATE AND EXPLAIN:
1. 🔢 Life Path Number (sum of birth date digits)
2. 💫 Destiny Number (sum of full name digits using Pythagorean table)
3. 🌟 Soul Number (vowels of the name)
4. 🎭 Personality Number (consonants)
5. 📅 Birth Day Number
6. 🔮 Personal Year Number (current year)

Show all calculations step by step. Give deep interpretation of each number. Style: serious, deep but warm. End with 3 specific recommendations.""",

    "de": """Du bist Aaron, ein Meister-Numerologe mit 25 Jahren Erfahrung. Analysiere AUSSCHLIESSLICH AUF DEUTSCH.

BERECHNE UND ERKLÄRE:
1. 🔢 Lebenspfadzahl (Summe der Geburtsdatumziffern)
2. 💫 Schicksalszahl (Summe der vollständigen Namensziffern nach Pythagoras)
3. 🌟 Seelenzahl (Vokale des Namens)
4. 🎭 Persönlichkeitszahl (Konsonanten)
5. 📅 Geburtstagszahl
6. 🔮 Persönliche Jahreszahl (aktuelles Jahr)

Zeige alle Berechnungen Schritt für Schritt. Gib tiefe Interpretation jeder Zahl. Stil: ernsthaft, tiefgründig aber warm. Ende mit 3 konkreten Empfehlungen."""
}

NATAL_PROMPT = {
    "uk": """Ти — Аарон, майстер астрології з 25-річним досвідом. Будуй натальну карту та аналізуй ВИКЛЮЧНО УКРАЇНСЬКОЮ.

СТРУКТУРА АНАЛІЗУ:
1. ☀️ Сонячний знак — ядро особистості
2. 🌙 Місячний знак — емоційна природа (розрахуй за датою і часом)
3. ⬆️ Аскендент/Знак Зростання — як людину сприймають оточуючі
4. 🪐 Ключові планети та їх положення
5. 🏠 Найважливіші будинки гороскопу
6. 💫 Сильні сторони натальної карти
7. ⚡ Виклики та уроки
8. 🌟 Основні теми життя цієї людини
9. 🔮 3-4 конкретні рекомендації

Стиль: глибокий, серйозний, мудрий. Покажи розрахунки де можливо.""",

    "ru": """Ты — Аарон, мастер астрологии с 25-летним опытом. Строй натальную карту и анализируй ИСКЛЮЧИТЕЛЬНО НА РУССКОМ.

СТРУКТУРА АНАЛИЗА:
1. ☀️ Солнечный знак — ядро личности
2. 🌙 Лунный знак — эмоциональная природа (рассчитай по дате и времени)
3. ⬆️ Асцендент — как человека воспринимают окружающие
4. 🪐 Ключевые планеты и их положения
5. 🏠 Важнейшие дома гороскопа
6. 💫 Сильные стороны натальной карты
7. ⚡ Вызовы и уроки
8. 🌟 Основные темы жизни этого человека
9. 🔮 3-4 конкретные рекомендации

Стиль: глубокий, серьёзный, мудрый. Покажи расчёты где возможно.""",

    "en": """You are Aaron, a master astrologer with 25 years of experience. Build the natal chart and analyze EXCLUSIVELY IN ENGLISH.

ANALYSIS STRUCTURE:
1. ☀️ Sun Sign — core personality
2. 🌙 Moon Sign — emotional nature (calculate from date and time)
3. ⬆️ Ascendant — how others perceive this person
4. 🪐 Key planets and their positions
5. 🏠 Most important houses
6. 💫 Strengths of the natal chart
7. ⚡ Challenges and lessons
8. 🌟 Main life themes for this person
9. 🔮 3-4 specific recommendations

Style: deep, serious, wise. Show calculations where possible.""",

    "de": """Du bist Aaron, ein Meister-Astrologe mit 25 Jahren Erfahrung. Erstelle das Geburtshoroskop und analysiere AUSSCHLIESSLICH AUF DEUTSCH.

ANALYSESTRUKTUR:
1. ☀️ Sonnenzeichen — Persönlichkeitskern
2. 🌙 Mondzeichen — emotionale Natur (berechne aus Datum und Zeit)
3. ⬆️ Aszendent — wie andere diese Person wahrnehmen
4. 🪐 Schlüsselplaneten und ihre Positionen
5. 🏠 Wichtigste Häuser
6. 💫 Stärken des Geburtshoroskops
7. ⚡ Herausforderungen und Lektionen
8. 🌟 Hauptlebensthemen dieser Person
9. 🔮 3-4 konkrete Empfehlungen

Stil: tiefgründig, ernsthaft, weise. Zeige Berechnungen wo möglich."""
}

COMPAT_PROMPT = {
    "uk": """Ти — Аарон, майстер астрології та нумерології. Аналізуй сумісність ВИКЛЮЧНО УКРАЇНСЬКОЮ.

СТРУКТУРА АНАЛІЗУ:
1. 🌟 Астрологічна сумісність (знаки зодіаку обох)
2. 🔢 Нумерологічна сумісність (числа життєвого шляху)
3. ❤️ Емоційна та романтична сумісність
4. 🤝 Ділова та дружня сумісність
5. ⚡ Точки напруги та як їх долати
6. 💫 Спільні сильні сторони
7. 🔮 Загальний прогноз стосунків
8. 💡 3 практичні поради для гармонії

Стиль: відвертий, глибокий, без прикрас, але з теплотою.""",

    "ru": """Ты — Аарон, мастер астрологии и нумерологии. Анализируй совместимость ИСКЛЮЧИТЕЛЬНО НА РУССКОМ.

СТРУКТУРА АНАЛИЗА:
1. 🌟 Астрологическая совместимость (знаки зодиака обоих)
2. 🔢 Нумерологическая совместимость (числа жизненного пути)
3. ❤️ Эмоциональная и романтическая совместимость
4. 🤝 Деловая и дружеская совместимость
5. ⚡ Точки напряжения и как их преодолевать
6. 💫 Общие сильные стороны
7. 🔮 Общий прогноз отношений
8. 💡 3 практических совета для гармонии

Стиль: откровенный, глубокий, без прикрас, но с теплотой.""",

    "en": """You are Aaron, a master astrologer and numerologist. Analyze compatibility EXCLUSIVELY IN ENGLISH.

ANALYSIS STRUCTURE:
1. 🌟 Astrological compatibility (both zodiac signs)
2. 🔢 Numerological compatibility (life path numbers)
3. ❤️ Emotional and romantic compatibility
4. 🤝 Business and friendship compatibility
5. ⚡ Tension points and how to overcome them
6. 💫 Shared strengths
7. 🔮 Overall relationship forecast
8. 💡 3 practical tips for harmony

Style: honest, deep, straightforward but warm.""",

    "de": """Du bist Aaron, ein Meister-Astrologe und Numerologe. Analysiere die Kompatibilität AUSSCHLIESSLICH AUF DEUTSCH.

ANALYSESTRUKTUR:
1. 🌟 Astrologische Kompatibilität (beide Tierkreiszeichen)
2. 🔢 Numerologische Kompatibilität (Lebenspfadzahlen)
3. ❤️ Emotionale und romantische Kompatibilität
4. 🤝 Geschäftliche und freundschaftliche Kompatibilität
5. ⚡ Spannungspunkte und wie man sie überwindet
6. 💫 Gemeinsame Stärken
7. 🔮 Gesamtprognose der Beziehung
8. 💡 3 praktische Tipps für Harmonie

Stil: ehrlich, tiefgründig, direkt aber warm."""
}

HOROSCOPE_PROMPT = {
    "uk": """Ти — Аарон, майстер астрології. Склади гороскоп ВИКЛЮЧНО УКРАЇНСЬКОЮ.

Визнач знак зодіаку за датою народження та склади детальний гороскоп:

📅 СЬОГОДНІ ({date_today}):
- Загальна енергія дня
- Любов і стосунки
- Робота і фінанси
- Здоров'я і самопочуття
- Щасливі числа та кольори дня

📅 ЗАВТРА ({date_tomorrow}):
- Загальна енергія дня
- Любов і стосунки
- Робота і фінанси
- Здоров'я і самопочуття
- Рада на завтра

Стиль: конкретний, практичний, надихаючий.""",

    "ru": """Ты — Аарон, мастер астрологии. Составь гороскоп ИСКЛЮЧИТЕЛЬНО НА РУССКОМ.

Определи знак зодиака по дате рождения и составь детальный гороскоп:

📅 СЕГОДНЯ ({date_today}):
- Общая энергия дня
- Любовь и отношения
- Работа и финансы
- Здоровье и самочувствие
- Счастливые числа и цвета дня

📅 ЗАВТРА ({date_tomorrow}):
- Общая энергия дня
- Любовь и отношения
- Работа и финансы
- Здоровье и самочувствие
- Совет на завтра

Стиль: конкретный, практичный, вдохновляющий.""",

    "en": """You are Aaron, a master astrologer. Compose the horoscope EXCLUSIVELY IN ENGLISH.

Determine the zodiac sign from the birth date and compose a detailed horoscope:

📅 TODAY ({date_today}):
- General energy of the day
- Love and relationships
- Work and finances
- Health and wellbeing
- Lucky numbers and colors

📅 TOMORROW ({date_tomorrow}):
- General energy of the day
- Love and relationships
- Work and finances
- Health and wellbeing
- Advice for tomorrow

Style: specific, practical, inspiring.""",

    "de": """Du bist Aaron, ein Meister-Astrologe. Erstelle das Horoskop AUSSCHLIESSLICH AUF DEUTSCH.

Bestimme das Tierkreiszeichen aus dem Geburtsdatum und erstelle ein detailliertes Horoskop:

📅 HEUTE ({date_today}):
- Allgemeine Energie des Tages
- Liebe und Beziehungen
- Arbeit und Finanzen
- Gesundheit und Wohlbefinden
- Glückszahlen und Farben

📅 MORGEN ({date_tomorrow}):
- Allgemeine Energie des Tages
- Liebe und Beziehungen
- Arbeit und Finanzen
- Gesundheit und Wohlbefinden
- Rat für morgen

Stil: konkret, praktisch, inspirierend."""
}

# ─────────────────────────────────────────────
# КЛАВИАТУРЫ
# ─────────────────────────────────────────────
def lang_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🇺🇦 Українська"), KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English"), KeyboardButton(text="🇩🇪 Deutsch")],
    ], resize_keyboard=True)

def menu_keyboard(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["menu_palm"]), KeyboardButton(text=t["menu_num"])],
        [KeyboardButton(text=t["menu_natal"]), KeyboardButton(text=t["menu_compat"])],
        [KeyboardButton(text=t["menu_horoscope"])],
    ], resize_keyboard=True)

def hand_keyboard(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["left_btn"]), KeyboardButton(text=t["right_btn"])],
        [KeyboardButton(text=t["both_btn"])],
        [KeyboardButton(text=t["back"])],
    ], resize_keyboard=True)

def back_keyboard(lang):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=TEXTS[lang]["back"])]
    ], resize_keyboard=True)

# ─────────────────────────────────────────────
# УТИЛИТЫ
# ─────────────────────────────────────────────
async def send_long(message: Message, text: str):
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000])

def get_lang(uid):
    return user_state.get(uid, {}).get("lang", "ru")

def all_buttons(key):
    return [TEXTS[l][key] for l in TEXTS]

from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# ХЭНДЛЕРЫ
# ─────────────────────────────────────────────
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🔮 Вітаю / Привет / Hello / Hallo!\n\nОберіть мову / Выберите язык / Choose language / Sprache wählen:",
        reply_markup=lang_keyboard()
    )

@dp.message(F.text.in_(["🇺🇦 Українська", "🇷🇺 Русский", "🇬🇧 English", "🇩🇪 Deutsch"]))
async def choose_language(message: Message):
    lang_map = {"🇺🇦 Українська": "uk", "🇷🇺 Русский": "ru", "🇬🇧 English": "en", "🇩🇪 Deutsch": "de"}
    lang = lang_map[message.text]
    user_state[message.from_user.id] = {"lang": lang, "step": "menu"}
    t = TEXTS[lang]
    await message.answer(t["choose_menu"], reply_markup=menu_keyboard(lang))

@dp.message(F.text.func(lambda t: t in all_buttons("back")))
async def go_back(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_state[uid] = {"lang": lang, "step": "menu"}
    await message.answer(TEXTS[lang]["choose_menu"], reply_markup=menu_keyboard(lang))

# ── ХИРОМАНТИЯ ──
@dp.message(F.text.func(lambda t: t in all_buttons("menu_palm")))
async def menu_palm(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_state[uid].update({"step": "palm_choose_hand", "mode": "palm"})
    await message.answer(TEXTS[lang]["choose_hand"], reply_markup=hand_keyboard(lang))

@dp.message(F.text.func(lambda t: t in all_buttons("left_btn")))
async def pick_left(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_state[uid].update({"hand": "left", "step": "palm_wait_photo"})
    await message.answer(TEXTS[lang]["send_left"], reply_markup=back_keyboard(lang))

@dp.message(F.text.func(lambda t: t in all_buttons("right_btn")))
async def pick_right(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_state[uid].update({"hand": "right", "step": "palm_wait_photo"})
    await message.answer(TEXTS[lang]["send_right"], reply_markup=back_keyboard(lang))

@dp.message(F.text.func(lambda t: t in all_buttons("both_btn")))
async def pick_both(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_state[uid].update({"hand": "both", "step": "palm_wait_left"})
    await message.answer(TEXTS[lang]["send_left"], reply_markup=back_keyboard(lang))

# ── НУМЕРОЛОГИЯ ──
@dp.message(F.text.func(lambda t: t in all_buttons("menu_num")))
async def menu_num(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_state[uid].update({"step": "num_wait_input", "mode": "num"})
    await message.answer(TEXTS[lang]["num_ask_name"], reply_markup=back_keyboard(lang))

# ── НАТАЛЬНАЯ КАРТА ──
@dp.message(F.text.func(lambda t: t in all_buttons("menu_natal")))
async def menu_natal(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_state[uid].update({"step": "natal_wait_input", "mode": "natal"})
    await message.answer(TEXTS[lang]["natal_ask"], reply_markup=back_keyboard(lang))

# ── СОВМЕСТИМОСТЬ ──
@dp.message(F.text.func(lambda t: t in all_buttons("menu_compat")))
async def menu_compat(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_state[uid].update({"step": "compat_wait_1", "mode": "compat"})
    await message.answer(TEXTS[lang]["compat_ask1"], reply_markup=back_keyboard(lang))

# ── ГОРОСКОП ──
@dp.message(F.text.func(lambda t: t in all_buttons("menu_horoscope")))
async def menu_horoscope(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_state[uid].update({"step": "horoscope_wait_date", "mode": "horoscope"})
    await message.answer(TEXTS[lang]["horoscope_ask"], reply_markup=back_keyboard(lang))

# ─────────────────────────────────────────────
# ОБРАБОТКА ФОТО
# ─────────────────────────────────────────────
@dp.message(F.photo)
async def handle_photo(message: Message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    lang = state.get("lang", "ru")
    t = TEXTS[lang]
    step = state.get("step", "")

    if step not in ("palm_wait_photo", "palm_wait_left", "palm_wait_right"):
        await message.answer(TEXTS[lang]["choose_menu"], reply_markup=menu_keyboard(lang))
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = f"photo_{uid}.jpg"
    await bot.download_file(file.file_path, file_path)

    with open(file_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    if os.path.exists(file_path):
        os.remove(file_path)

    # Ждём вторую руку
    if step == "palm_wait_left":
        user_state[uid].update({"left_photo": img_data, "step": "palm_wait_right"})
        await message.answer(t["send_second"])
        return

    if step == "palm_wait_right":
        await message.answer(t["analyzing_both"])
        first_img = state.get("left_photo")
        try:
            response = model.generate_content([
                PALM_SYSTEM[lang],
                {"inline_data": {"mime_type": "image/jpeg", "data": first_img}},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_data}},
                PALM_PROMPTS[lang]["both"]
            ])
            await send_long(message, response.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["palm_error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_keyboard(lang))
        return

    # Одна рука
    hand = state.get("hand", "right")
    await message.answer(t["analyzing"])
    try:
        response = model.generate_content([
            PALM_SYSTEM[lang],
            {"inline_data": {"mime_type": "image/jpeg", "data": img_data}},
            PALM_PROMPTS[lang][hand]
        ])
        await send_long(message, response.text)
    except Exception as e:
        logging.error(e)
        await message.answer(t["palm_error"])

    user_state[uid].update({"step": "menu"})
    await message.answer(t["choose_menu"], reply_markup=menu_keyboard(lang))

# ─────────────────────────────────────────────
# ОБРАБОТКА ТЕКСТА (ввод данных)
# ─────────────────────────────────────────────
@dp.message(F.text)
async def handle_text_input(message: Message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    lang = state.get("lang", "ru")
    t = TEXTS[lang]
    step = state.get("step", "menu")
    text = message.text.strip()

    # Нумерология
    if step == "num_wait_input":
        await message.answer(t["num_analyzing"])
        try:
            response = model.generate_content(
                NUMEROLOGY_PROMPT[lang] + f"\n\nДані користувача / Данные: {text}"
            )
            await send_long(message, response.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_keyboard(lang))

    # Натальная карта
    elif step == "natal_wait_input":
        await message.answer(t["natal_analyzing"])
        try:
            response = model.generate_content(
                NATAL_PROMPT[lang] + f"\n\nДані: {text}"
            )
            await send_long(message, response.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_keyboard(lang))

    # Совместимость — первый человек
    elif step == "compat_wait_1":
        user_state[uid].update({"compat_1": text, "step": "compat_wait_2"})
        await message.answer(t["compat_ask2"])

    # Совместимость — второй человек
    elif step == "compat_wait_2":
        person1 = state.get("compat_1", "")
        await message.answer(t["compat_analyzing"])
        try:
            prompt = COMPAT_PROMPT[lang] + f"\n\nПерша людина / Человек 1: {person1}\nДруга людина / Человек 2: {text}"
            response = model.generate_content(prompt)
            await send_long(message, response.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_keyboard(lang))

    # Гороскоп
    elif step == "horoscope_wait_date":
        await message.answer(t["horoscope_analyzing"])
        today = datetime.now().strftime("%d.%m.%Y")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
        try:
            prompt = HOROSCOPE_PROMPT[lang].format(
                date_today=today, date_tomorrow=tomorrow
            ) + f"\n\nДата народження / Дата рождения: {text}"
            response = model.generate_content(prompt)
            await send_long(message, response.text)
        except Exception as e:
            logging.error(e)
            await message.answer(t["error"])
        user_state[uid].update({"step": "menu"})
        await message.answer(t["choose_menu"], reply_markup=menu_keyboard(lang))

    else:
        await message.answer(t["choose_menu"], reply_markup=menu_keyboard(lang))

# ─────────────────────────────────────────────
async def main():
    print("🔮 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
