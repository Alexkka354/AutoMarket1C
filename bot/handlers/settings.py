from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.requests import get_or_create_user, save_user_settings, get_user_settings

router = Router()

class SettingsState(StatesGroup):
    waiting_for_category = State()
    waiting_for_schedule = State()

@router.callback_query(lambda c: c.data == "settings")
async def show_settings(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_user_settings(callback.from_user.id)
    current = ""
    if user and user.category:
        current = f"\n\n📌 Текущие настройки:\n• Категория: {user.category}\n• Синхронизация: каждые {user.schedule_minutes} мин."
    await callback.message.answer(
        f"⚙️ Настройки выгрузки{current}\n\n"
        "Введите категорию товаров для выгрузки\n"
        "(например: Электроника, Одежда, Мебель):"
    )
    await state.set_state(SettingsState.waiting_for_category)

@router.message(SettingsState.waiting_for_category)
async def process_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer(
        f"✅ Категория: {message.text}\n\n"
        "Введите интервал синхронизации в минутах\n"
        "(например: 30):"
    )
    await state.set_state(SettingsState.waiting_for_schedule)

@router.message(SettingsState.waiting_for_schedule)
async def process_schedule(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число, например: 30")
        return
    schedule = int(message.text)
    data = await state.get_data()
    await get_or_create_user(message.from_user.id, message.from_user.username)
    await save_user_settings(message.from_user.id, data['category'], schedule)
    await state.clear()
    await message.answer(
        f"✅ Настройки сохранены в базе данных!\n\n"
        f"📦 Категория: {data['category']}\n"
        f"⏱ Синхронизация каждые {schedule} мин."
    )