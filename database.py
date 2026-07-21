import asyncpg
import logging
import random
import string
from datetime import datetime, timedelta
from config import DATABASE_URL, FREE_LIMIT, ADMIN_IDS

db_pool = None


async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       BIGINT PRIMARY KEY,
                lang          TEXT      DEFAULT 'ru',
                free_uses     INT       DEFAULT 0,
                is_subscribed BOOL      DEFAULT FALSE,
                sub_until     TIMESTAMP,
                plan          INT       DEFAULT 0,
                ref_code      TEXT      UNIQUE,
                referred_by   BIGINT,
                created_at    TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date TEXT")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_time TEXT")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_enabled BOOL DEFAULT FALSE")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan INT DEFAULT 0")

        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_year INT")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_month INT")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_day INT")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_hour INT")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_minute INT")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_city TEXT")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS crypto_invoices (
                invoice_id  BIGINT PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                plan        TEXT   NOT NULL,
                amount      TEXT,
                asset       TEXT,
                status      TEXT   DEFAULT 'pending',
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS visit_log (
                id          BIGSERIAL PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                visited_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reading_log (
                id            BIGSERIAL PRIMARY KEY,
                user_id       BIGINT NOT NULL,
                reading_type  TEXT NOT NULL,
                created_at    TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payments_log (
                id          BIGSERIAL PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                plan        INT NOT NULL,
                currency    TEXT NOT NULL,
                amount      TEXT,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
    logging.info("DB ready")


def gen_ref_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


async def get_or_create_user(user_id: int) -> dict:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        if not row:
            code = gen_ref_code()
            while await conn.fetchrow("SELECT 1 FROM users WHERE ref_code=$1", code):
                code = gen_ref_code()
            await conn.execute(
                "INSERT INTO users (user_id, ref_code) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                user_id, code
            )
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        return dict(row)


async def save_lang(user_id: int, lang: str):
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET lang=$1 WHERE user_id=$2", lang, user_id)


async def increment_uses(user_id: int):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET free_uses = free_uses + 1 WHERE user_id=$1", user_id
        )


async def can_use(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    user = await get_or_create_user(user_id)
    if user['is_subscribed'] and user['sub_until'] and user['sub_until'] > datetime.now():
        return True
    return (user['free_uses'] or 0) < FREE_LIMIT


async def activate_subscription(user_id: int, plan: int, days: int = 30):
    async with db_pool.acquire() as conn:
        row  = await conn.fetchrow("SELECT sub_until FROM users WHERE user_id=$1", user_id)
        now  = datetime.now()
        base = row['sub_until'] if (row['sub_until'] and row['sub_until'] > now) else now
        await conn.execute(
            "UPDATE users SET is_subscribed=TRUE, sub_until=$1, plan=$2 WHERE user_id=$3",
            base + timedelta(days=days), plan, user_id
        )


async def give_ref_bonus(referrer_id: int, days: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT sub_until, plan FROM users WHERE user_id=$1", referrer_id
        )
        if not row:
            return
        now      = datetime.now()
        base     = row['sub_until'] if (row['sub_until'] and row['sub_until'] > now) else now
        new_plan = (row['plan'] or 0) if (row['plan'] or 0) > 0 else 1
        await conn.execute(
            "UPDATE users SET is_subscribed=TRUE, sub_until=$1, plan=$2 WHERE user_id=$3",
            base + timedelta(days=days), new_plan, referrer_id
        )


async def save_notify_settings(
    user_id: int,
    birth_date: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int,
    birth_city: str,
    notify_time: str,
):
    """
    Сохраняет полный набор данных для ежедневного персонального гороскопа
    (структурированные поля — для FreeAstroAPI, birth_date — для показа юзеру)
    и включает рассылку.
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET birth_date=$1, birth_year=$2, birth_month=$3, birth_day=$4,
                birth_hour=$5, birth_minute=$6, birth_city=$7,
                notify_time=$8, notify_enabled=TRUE
            WHERE user_id=$9
            """,
            birth_date, birth_year, birth_month, birth_day,
            birth_hour, birth_minute, birth_city,
            notify_time, user_id
        )


async def get_premium_notify_users(now_time: str) -> list:
    """
    Возвращает Premium-подписчиков (+ админов) с включённой рассылкой,
    у кого сейчас наступило выбранное время доставки и есть полные данные рождения.
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, lang, notify_time,
                   birth_year, birth_month, birth_day,
                   birth_hour, birth_minute, birth_city
            FROM users
            WHERE notify_enabled = TRUE
              AND notify_time = $1
              AND birth_year IS NOT NULL
              AND birth_month IS NOT NULL
              AND birth_day IS NOT NULL
              AND birth_city IS NOT NULL
              AND (
                  (is_subscribed = TRUE AND sub_until > NOW() AND plan = 2)
                  OR user_id = ANY($2)
              )
        """, now_time, list(ADMIN_IDS))
    return rows


async def create_crypto_invoice(invoice_id: int, user_id: int, plan: str, amount: str, asset: str):
    """Сохраняет созданный в CryptoBot инвойс со статусом 'pending'."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO crypto_invoices (invoice_id, user_id, plan, amount, asset, status)
            VALUES ($1, $2, $3, $4, $5, 'pending')
            ON CONFLICT (invoice_id) DO NOTHING
            """,
            invoice_id, user_id, plan, amount, asset
        )


async def get_pending_crypto_invoices() -> list:
    """Все инвойсы, ожидающие оплаты — для периодической проверки статуса."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT invoice_id, user_id, plan, amount FROM crypto_invoices WHERE status='pending'"
        )
    return rows


async def mark_crypto_invoice_status(invoice_id: int, status: str):
    """Обновляет статус инвойса (paid / expired / pending)."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE crypto_invoices SET status=$1 WHERE invoice_id=$2",
            status, invoice_id
        )


async def get_crypto_invoice(invoice_id: int) -> dict | None:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM crypto_invoices WHERE invoice_id=$1", invoice_id
        )
    return dict(row) if row else None


async def get_latest_pending_invoice(user_id: int) -> dict | None:
    """
    Последний неоплаченный инвойс пользователя — используется кнопкой
    'Проверить оплату', устойчиво к перезапуску бота (не зависит от user_state).
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM crypto_invoices
            WHERE user_id=$1 AND status='pending'
            ORDER BY created_at DESC LIMIT 1
            """,
            user_id
        )
    return dict(row) if row else None


# ─────────────────────────────────────────────
# ЛОГИРОВАНИЕ (для админ-панели)
# ─────────────────────────────────────────────

async def log_visit(user_id: int):
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO visit_log (user_id) VALUES ($1)", user_id)


async def log_reading(user_id: int, reading_type: str):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO reading_log (user_id, reading_type) VALUES ($1, $2)",
            user_id, reading_type
        )


async def log_payment(user_id: int, plan: int, currency: str, amount: str):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO payments_log (user_id, plan, currency, amount) VALUES ($1, $2, $3, $4)",
            user_id, plan, currency, amount
        )


# ─────────────────────────────────────────────
# СТАТИСТИКА (для админ-панели)
# ─────────────────────────────────────────────

async def get_stats_overview() -> dict:
    async with db_pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        new_today = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE created_at::date = CURRENT_DATE"
        )
        new_week = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '7 days'"
        )
        dau = await conn.fetchval(
            "SELECT COUNT(DISTINCT user_id) FROM visit_log WHERE visited_at::date = CURRENT_DATE"
        )
        wau = await conn.fetchval(
            "SELECT COUNT(DISTINCT user_id) FROM visit_log WHERE visited_at >= NOW() - INTERVAL '7 days'"
        )
        total_readings = await conn.fetchval("SELECT COUNT(*) FROM reading_log")
        readings_today = await conn.fetchval(
            "SELECT COUNT(*) FROM reading_log WHERE created_at::date = CURRENT_DATE"
        )
        active_subs = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE is_subscribed = TRUE AND sub_until > NOW()"
        )
        revenue_today = await conn.fetch(
            """
            SELECT currency, plan, COUNT(*) as cnt
            FROM payments_log
            WHERE created_at::date = CURRENT_DATE
            GROUP BY currency, plan
            """
        )
        revenue_total = await conn.fetch(
            """
            SELECT currency, plan, COUNT(*) as cnt
            FROM payments_log
            GROUP BY currency, plan
            """
        )
    return {
        "total_users": total_users,
        "new_today": new_today,
        "new_week": new_week,
        "dau": dau,
        "wau": wau,
        "total_readings": total_readings,
        "readings_today": readings_today,
        "active_subs": active_subs,
        "revenue_today": [dict(r) for r in revenue_today],
        "revenue_total": [dict(r) for r in revenue_total],
    }


async def get_reading_stats() -> list:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT reading_type, COUNT(*) as cnt
            FROM reading_log
            GROUP BY reading_type
            ORDER BY cnt DESC
            """
        )
    return [dict(r) for r in rows]


async def get_referral_stats() -> dict:
    async with db_pool.acquire() as conn:
        total_referred = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL"
        )
        converted = await conn.fetchval(
            """
            SELECT COUNT(*) FROM users
            WHERE referred_by IS NOT NULL AND is_subscribed = TRUE
            """
        )
        top_referrers = await conn.fetch(
            """
            SELECT referred_by AS user_id, COUNT(*) as cnt
            FROM users
            WHERE referred_by IS NOT NULL
            GROUP BY referred_by
            ORDER BY cnt DESC
            LIMIT 10
            """
        )
    return {
        "total_referred": total_referred,
        "converted": converted,
        "top_referrers": [dict(r) for r in top_referrers],
    }


async def get_users_page(offset: int = 0, limit: int = 10) -> list:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id, lang, plan, is_subscribed, sub_until, free_uses, created_at
            FROM users
            ORDER BY created_at DESC
            OFFSET $1 LIMIT $2
            """,
            offset, limit
        )
    return [dict(r) for r in rows]
