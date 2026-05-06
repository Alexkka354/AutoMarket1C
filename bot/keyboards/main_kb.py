from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Запустить выгрузку", callback_data="upload_start")],
        [InlineKeyboardButton(text="⏹ Остановить выгрузку", callback_data="upload_stop")],
        [InlineKeyboardButton(text="🤖 Генерация контента", callback_data="generate_content")],
        [InlineKeyboardButton(text="📘 Опубликовать в ВК",  callback_data="vk_publish")],
        [InlineKeyboardButton(text="📦 Товары в ВК",        callback_data="vk_products")],
        [InlineKeyboardButton(text="📊 Аналитика",          callback_data="analytics")],
        [InlineKeyboardButton(text="⚙️ Настройки",          callback_data="settings")],
    ])
def persistent_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главное меню")],
            [KeyboardButton(text="🚀 Выгрузка"), KeyboardButton(text="📊 Аналитика")],
            [KeyboardButton(text="🤖 Генерация"), KeyboardButton(text="📘 ВКонтакте")],
        ],
        resize_keyboard=True,
        persistent=True
    )