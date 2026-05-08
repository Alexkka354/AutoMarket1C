from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from integration_module.client import get_products, force_sync, publish_to_avito

router = Router()

class UploadState(StatesGroup):
    waiting_for_platform = State()

def platform_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Авито",        callback_data="platform_avito")],
        [InlineKeyboardButton(text="📘 ВКонтакте",    callback_data="platform_vk")],
        [InlineKeyboardButton(text="🌐 Все площадки", callback_data="platform_all")],
    ])

@router.callback_query(lambda c: c.data == "upload_start")
async def upload_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "🚀 Выберите площадку для выгрузки:",
        reply_markup=platform_keyboard()
    )

@router.callback_query(lambda c: c.data.startswith("platform_"))
async def select_platform(callback: CallbackQuery, state: FSMContext):
    platform_map = {
        "platform_avito": "Авито",
        "platform_vk": "ВКонтакте",
        "platform_all": "Все площадки"
    }
    platform = platform_map.get(callback.data, "Неизвестно")
    await callback.answer()
    await callback.message.answer(f"⏳ Запускаю синхронизацию с 1С...")

    try:
        sync_result = await force_sync()
        if sync_result.get("status") == "ok":
            synced = sync_result.get("synced", 0)

            if callback.data == "platform_avito" or callback.data == "platform_all":
                publish_result = await publish_to_avito()
                published = publish_result.get("published", 0)
                await callback.message.answer(
                    f"✅ Синхронизация завершена!\n\n"
                    f"📦 Загружено товаров: {synced}\n"
                    f"🏪 Площадка: {platform}\n"
                    f"📌 Опубликовано на Авито: {published}\n\n"
                    f"Товары доступны на странице Авито."
                )
            else:
                await callback.message.answer(
                    f"✅ Синхронизация завершена!\n\n"
                    f"📦 Загружено товаров: {synced}\n"
                    f"🏪 Площадка: {platform}\n\n"
                    f"Теперь можно публиковать товары."
                )
        else:
            await callback.message.answer(
                f"⚠️ Синхронизация недоступна — адаптер 1С не запущен.\n"
                f"Попробуйте позже или запустите адаптер 1С."
            )
    except Exception:
        await callback.message.answer(
            f"⚠️ Адаптер 1С недоступен.\n"
            f"Убедитесь что интеграционный модуль запущен на порту 8000."
        )

@router.callback_query(lambda c: c.data == "upload_stop")
async def upload_stop(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer("⏹ Выгрузка остановлена.")
