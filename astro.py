import asyncio
import logging
from datetime import datetime

import requests

from config import FREE_ASTRO_API_KEY, FREE_ASTRO_BASE_URL

DAILY_PERSONAL_URL = f"{FREE_ASTRO_BASE_URL}/api/v3/horoscope/daily/personal"
REQUEST_TIMEOUT = 15  # секунд


def _fetch_daily_personal_sync(
    year: int, month: int, day: int, hour: int, minute: int,
    city: str, date: str
) -> dict | None:
    """
    Синхронный запрос к FreeAstroAPI. Возвращает распарсенные данные
    или None при любой ошибке (сеть, лимиты, невалидные данные) —
    вызывающий код обязан уметь работать без этих данных (fallback).
    """
    if not FREE_ASTRO_API_KEY:
        logging.error("FREE_ASTRO_API_KEY is not set")
        return None

    payload = {
        "birth": {
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "city": city,
            "tz_str": "AUTO",
            "time_known": True,
        },
        "date": date,
        "include_interpretation_blocks": True,
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": FREE_ASTRO_API_KEY,
    }

    try:
        resp = requests.post(
            DAILY_PERSONAL_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        logging.error(f"FreeAstroAPI request failed: {e}")
        return None

    try:
        data = raw["data"]
        content = data.get("content", {}) or {}
        personal = data.get("personal", {}) or {}
        day_context = personal.get("day_context", {}) or {}

        transits_top = []
        for t in (personal.get("transits_top") or [])[:3]:
            transits_top.append({
                "label": t.get("label", ""),
                "explanation": (t.get("explanation") or {}).get("main", ""),
            })

        dominant_topics = [
            topic.get("title", "")
            for topic in (day_context.get("dominant_topics") or [])
            if topic.get("title")
        ]

        return {
            "sign": data.get("sign", ""),
            "scores": data.get("scores", {}),
            "theme": content.get("theme", ""),
            "keywords": content.get("keywords", []),
            "focus_areas": personal.get("focus_areas", []),
            "transits_top": transits_top,
            "dominant_topics": dominant_topics,
        }
    except Exception as e:
        logging.error(f"FreeAstroAPI response parsing failed: {e}")
        return None


async def get_daily_personal_horoscope(
    year: int, month: int, day: int, hour: int, minute: int,
    city: str, date: str | None = None
) -> dict | None:
    """
    Асинхронная обёртка. date в формате YYYY-MM-DD, по умолчанию — сегодня.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _fetch_daily_personal_sync, year, month, day, hour, minute, city, date
    )


def format_astro_facts(facts: dict) -> str:
    """
    Превращает распарсенные данные FreeAstroAPI в компактный текстовый блок
    фактов для передачи в промпт Groq — модель не выдумывает астрологию,
    а красиво облекает в слова уже посчитанные реальные данные.
    """
    if not facts:
        return ""

    lines = []
    if facts.get("theme"):
        lines.append(f"Тема дня: {facts['theme']}")
    if facts.get("keywords"):
        lines.append(f"Ключевые слова: {', '.join(facts['keywords'])}")
    scores = facts.get("scores") or {}
    if scores:
        scores_str = ", ".join(f"{k}: {v}/100" for k, v in scores.items())
        lines.append(f"Оценки дня: {scores_str}")
    if facts.get("focus_areas"):
        lines.append(f"Основные сферы внимания: {', '.join(facts['focus_areas'])}")
    if facts.get("transits_top"):
        lines.append("Активные транзиты:")
        for t in facts["transits_top"]:
            line = f"- {t['label']}"
            if t.get("explanation"):
                line += f": {t['explanation']}"
            lines.append(line)
    if facts.get("dominant_topics"):
        lines.append(f"Общая тема периода: {', '.join(facts['dominant_topics'])}")

    return "\n".join(lines)
