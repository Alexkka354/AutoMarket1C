from aiogram import Router
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(lambda c: c.data == "analytics")
async def show_analytics(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📊 Аналитика за последние 7 дней\n\n"
        "👁 Просмотры:       1 204\n"
        "🖱 Клики:            347\n"
        "💬 Отклики:          28\n"
        "✅ Продажи:          12\n"
        "📈 Конверсия:        3.4%\n\n"
        "🔮 Прогноз спроса на след. неделю: +15%\n\n"
        "_(данные тестовые, скоро подключим реальные)_"
    )