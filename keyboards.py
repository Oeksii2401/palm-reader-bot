from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from texts import TEXTS


def lang_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🇺🇦 Українська"), KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English"),    KeyboardButton(text="🇩🇪 Deutsch")],
    ], resize_keyboard=True)


def menu_kb(lang: str):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["menu_palm"]),      KeyboardButton(text=t["menu_num"])],
        [KeyboardButton(text=t["menu_natal"]),     KeyboardButton(text=t["menu_compat"])],
        [KeyboardButton(text=t["menu_horoscope"]), KeyboardButton(text=t["menu_name"])],
        [KeyboardButton(text=t["exit_btn"])],
    ], resize_keyboard=True)


def hand_kb(lang: str):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["left_btn"]), KeyboardButton(text=t["right_btn"])],
        [KeyboardButton(text=t["both_btn"])],
        [KeyboardButton(text=t["back"])],
    ], resize_keyboard=True)


def back_kb(lang: str):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=TEXTS[lang]["back"])]
    ], resize_keyboard=True)


def paywall_kb(lang: str):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["sub_standard_btn"])],
        [KeyboardButton(text=t["sub_standard_crypto_btn"])],
        [KeyboardButton(text=t["sub_premium_btn"])],
        [KeyboardButton(text=t["sub_premium_crypto_btn"])],
        [KeyboardButton(text=t["back"])],
    ], resize_keyboard=True)


def crypto_wait_kb(lang: str):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["crypto_check_btn"])],
        [KeyboardButton(text=t["back"])],
    ], resize_keyboard=True)


ALL_STANDARD_BTNS        = {TEXTS[l]["sub_standard_btn"]        for l in TEXTS}
ALL_PREMIUM_BTNS         = {TEXTS[l]["sub_premium_btn"]         for l in TEXTS}
ALL_STANDARD_CRYPTO_BTNS = {TEXTS[l]["sub_standard_crypto_btn"] for l in TEXTS}
ALL_PREMIUM_CRYPTO_BTNS  = {TEXTS[l]["sub_premium_crypto_btn"]  for l in TEXTS}
ALL_CRYPTO_CHECK_BTNS    = {TEXTS[l]["crypto_check_btn"]        for l in TEXTS}
