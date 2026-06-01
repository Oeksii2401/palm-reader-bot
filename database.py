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


async def get_premium_notify_users(now_time: str) -> list:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, lang, birth_date, notify_time
            FROM users
            WHERE notify_enabled = TRUE
              AND notify_time = $1
              AND birth_date IS NOT NULL
              AND (
                  (is_subscribed = TRUE AND sub_until > NOW() AND plan = 2)
                  OR user_id = ANY($2)
              )
        """, now_time, list(ADMIN_IDS))
    return rows