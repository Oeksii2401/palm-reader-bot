# Глобальный словарь состояний пользователей.
# Хранится в памяти — сбрасывается при перезапуске (например, при редеплое на Railway).
# Структура: { user_id: {"lang": "ru", "step": "menu", ...} }

user_state: dict = {}


def get_state(uid: int) -> dict:
    """
    Возвращает состояние пользователя.
    Если записи ещё нет (после рестарта бота или для нового юзера) —
    создаёт её со значениями по умолчанию, чтобы дальнейшие
    user_state[uid].update(...) не падали с KeyError.
    """
    if uid not in user_state:
        user_state[uid] = {"lang": "ru", "step": "lang"}
    return user_state[uid]
