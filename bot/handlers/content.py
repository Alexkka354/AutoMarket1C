from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from content.generator import generate_title, generate_description, classify_category

router = Router()

class ContentState(StatesGroup):
    waiting_for_product = State()

@router.callback_query(lambda c: c.data == "generate_content")
async def start_generate(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "🤖 Генерация контента с помощью ИИ\n\n"
        "Введите название и характеристики товара\n"
        "Например: Смартфон Samsung Galaxy A54, 8GB RAM, 256GB, черный"
    )
    await state.set_state(ContentState.waiting_for_product)

@router.message(ContentState.waiting_for_product)
async def process_product(message: Message, state: FSMContext):
    await state.clear()
    product = message.text
    await message.answer("⏳ Генерирую контент, подождите...")
    
    try:
        title = await generate_title(product, product)
        description = await generate_description(product, product, "Авито")
        category = await classify_category(product, product)
        
        await message.answer(
            f"✅ Контент сгенерирован!\n\n"
            f"📌 Заголовок:\n{title}\n\n"
            f"📝 Описание:\n{description}\n\n"
            f"🗂 Категория: {category}"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации: {str(e)}")