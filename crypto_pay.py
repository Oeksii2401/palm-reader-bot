import asyncio
import logging

import requests

from config import CRYPTO_PAY_API_KEY, CRYPTO_PAY_BASE_URL

REQUEST_TIMEOUT = 15  # секунд


def _call_sync(method: str, params: dict) -> dict | None:
    """
    Синхронный вызов Crypto Pay API. Возвращает содержимое поля "result"
    при успехе, либо None при любой ошибке (сеть/невалидный ответ/API-ошибка).
    """
    if not CRYPTO_PAY_API_KEY:
        logging.error("CRYPTO_PAY_API_KEY is not set")
        return None

    url = f"{CRYPTO_PAY_BASE_URL}/api/{method}"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_API_KEY}

    try:
        resp = requests.post(url, json=params, headers=headers, timeout=REQUEST_TIMEOUT)
        data = resp.json()
    except Exception as e:
        logging.error(f"Crypto Pay API request failed ({method}): {e}")
        return None

    if not data.get("ok"):
        logging.error(f"Crypto Pay API error ({method}): {data.get('error')}")
        return None

    return data.get("result")


async def create_invoice(amount: str, asset: str, description: str, payload: str) -> dict | None:
    """
    Создаёт инвойс на оплату. Возвращает dict с invoice_id и ссылкой на оплату
    (bot_invoice_url) либо None при ошибке.
    """
    loop = asyncio.get_event_loop()
    params = {
        "currency_type": "crypto",
        "asset": asset,
        "amount": amount,
        "description": description,
        "payload": payload,
        # 30 минут на оплату — если не успел, инвойс истечёт и просто останется висеть pending
        "expires_in": 1800,
    }
    return await loop.run_in_executor(None, _call_sync, "createInvoice", params)


async def get_invoice_status(invoice_id: int) -> str | None:
    """
    Возвращает текущий статус инвойса ("active" / "paid" / "expired")
    либо None, если не удалось получить.
    """
    loop = asyncio.get_event_loop()
    params = {"invoice_ids": str(invoice_id)}
    result = await loop.run_in_executor(None, _call_sync, "getInvoices", params)
    if not result:
        return None
    items = result.get("items") if isinstance(result, dict) else result
    if not items:
        return None
    return items[0].get("status")
