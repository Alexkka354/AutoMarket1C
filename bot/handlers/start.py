from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from bot.keyboards.main_kb import main_menu, persistent_keyboard
from database.requests import get_or_create_user

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await get_or_create_user(message.from_user.id, message.from_user.username)
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот управления выгрузкой товаров на Авито и ВКонтакте.\n\n"
        "Выберите действие:",
        reply_markup=persistent_keyboard()
    )
    await message.answer(
        "📋 Основное меню:",
        reply_markup=main_menu()
    )

@router.message(lambda m: m.text == "🏠 Главное меню")
async def main_menu_handler(message: Message):
    await message.answer(
        "📋 Основное меню:",
        reply_markup=main_menu()
    )

@router.message(lambda m: m.text == "🚀 Выгрузка")
async def upload_handler(message: Message):
    await message.answer(
        "🚀 Управление выгрузкой:",
        reply_markup=main_menu()
    )

@router.message(lambda m: m.text == "📊 Аналитика")
async def analytics_handler(message: Message):
    from integration_module.client import get_analytics
    await message.answer("⏳ Загружаю аналитику...")
    try:
        stats = await get_analytics()
        if stats:
            await message.answer(
                f"📊 Аналитика\n\n"
                f"📦 Товаров в базе: {stats.get('products_count', 0)}\n"
                f"✅ Активных: {stats.get('active_products', 0)}\n"
                f"🔄 Последняя синхронизация: {stats.get('last_sync', 'нет данных')}"
            )
        else:
            await message.answer("⚠️ Аналитика недоступна.")
    except Exception:
        await message.answer("⚠️ Интеграционный модуль не запущен.")

@router.message(lambda m: m.text == "🤖 Генерация")
async def generation_handler(message: Message):
    await message.answer(
        "🤖 Генерация контента с помощью ИИ\n\n"
        "Введите название и характеристики товара:"
    )
    from aiogram.fsm.context import FSMContext
    from bot.handlers.content import ContentState

@router.message(lambda m: m.text == "📘 ВКонтакте")
async def vk_handler(message: Message):
    await message.answer(
        "📘 Публикация товара ВКонтакте\n\n"
        "Введите название и характеристики товара:"
    )