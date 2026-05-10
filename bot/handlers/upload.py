from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from integration_module.client import get_products, publish_to_avito, update_product
from content.generator import generate_description, classify_category
from content.image_search import search_product_image
from vk.market import add_product
from config import INTEGRATION_URL
import aiohttp
import logging

router = Router()
logger = logging.getLogger(__name__)


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
        "platform_vk":    "ВКонтакте",
        "platform_all":   "Все площадки"
    }
    platform = platform_map.get(callback.data, "Неизвестно")
    await callback.answer()

    await callback.message.answer("⏳ Получаю товары из базы данных...")

    try:
        products = await get_products()

        if not products:
            await callback.message.answer(
                "⚠️ В базе данных нет активных товаров.\n"
                "Сначала выполните синхронизацию с 1С."
            )
            return

        await callback.message.answer(
            f"📦 Найдено товаров: {len(products)}\n"
            f"🤖 Начинаю интеллектуальную обработку карточек..."
        )

        processed = 0
        failed    = 0
        no_image  = 0

        for product in products:
            try:
                name    = product.get("name", "")
                article = product.get("article", "")
                price   = product.get("price", 0)
                stock   = product.get("stock", 0)

                # Шаг 1 — генерируем описание через GigaChat
                description = product.get("description")
                if not description:
                    try:
                        description = await generate_description(
                            name=name,
                            characteristics=(
                                f"Артикул: {article}, "
                                f"Цена: {price} ₽, "
                                f"В наличии: {stock} шт."
                            ),
                            platform=platform
                        )
                    except Exception as e:
                        logger.warning(f"GigaChat недоступен для {name}: {e}")
                        description = (
                            f"{name}\n\n"
                            f"Артикул: {article}\n"
                            f"Цена: {price} ₽\n"
                            f"В наличии: {stock} шт.\n"
                            f"Быстрая доставка. Гарантия качества."
                        )

                # Шаг 2 — определяем категорию через GigaChat
                category = product.get("category")
                if not category and callback.data in ("platform_avito", "platform_all"):
                    try:
                        category = await classify_category(
                            name=name,
                            description=description
                        )
                    except Exception as e:
                        logger.warning(f"Ошибка категоризации для {name}: {e}")

                # Шаг 3 — ищем фото через Яндекс.Картинки
                image_url = product.get("image_url")
                if not image_url:
                    try:
                        img_result = await search_product_image(
                            name, max_results=3
                        )
                        urls      = img_result.get("urls", [])
                        image_url = urls[0] if urls else None
                        if not image_url:
                            no_image += 1
                    except Exception as e:
                        logger.warning(f"Ошибка поиска фото для {name}: {e}")
                        no_image += 1

                # Шаг 4 — сохраняем описание, фото и категорию в БД
                await update_product(
                    product_id=product["id"],
                    description=description,
                    image_url=image_url,
                    category=category
                )

                product["description"] = description
                product["image_url"]   = image_url
                product["category"]    = category

                processed += 1

            except Exception as e:
                logger.error(
                    f"Ошибка обработки товара {product.get('name')}: {e}"
                )
                failed += 1

        await callback.message.answer(
            f"✅ Обработка завершена!\n\n"
            f"📦 Обработано товаров: {processed}\n"
            f"🖼 Без фото: {no_image}\n"
            f"❌ Ошибок: {failed}\n\n"
            f"⏳ Запускаю публикацию на {platform}..."
        )

        # Шаг 5 — публикуем на Авито (HTML-сайт)
        if callback.data in ("platform_avito", "platform_all"):
            try:
                result = await publish_to_avito()
                published = result.get("published", 0)
                await callback.message.answer(
                    f"📌 Авито:\n"
                    f"✅ Опубликовано {published} товаров\n"
                    f"🌐 Товары доступны на странице Авито"
                )
            except Exception as e:
                await callback.message.answer(
                    f"⚠️ Ошибка публикации на Авито: {str(e)}"
                )

        # Шаг 6 — публикуем в ВКонтакте
        if callback.data in ("platform_vk", "platform_all"):
            await callback.message.answer("📘 Публикую товары ВКонтакте...")

            vk_success = 0
            vk_failed  = 0

            for product in products:
                try:
                    name        = product.get("name", "")
                    price       = float(product.get("price", 0))
                    description = product.get("description") or (
                        f"{name}\n\n"
                        f"Артикул: {product.get('article', '')}\n"
                        f"В наличии: {product.get('stock', 0)} шт."
                    )
                    image_url   = product.get("image_url")

                    result = await add_product(
                        title=name[:100],
                        description=description,
                        price=price,
                        photo_url=image_url
                    )

                    if "response" in result:
                        vk_success += 1
                    else:
                        error = result.get("error", {}).get(
                            "error_msg", "Неизвестная ошибка"
                        )
                        logger.error(f"ВК ошибка для {name}: {error}")
                        vk_failed += 1

                except Exception as e:
                    logger.error(
                        f"Ошибка публикации в ВК для "
                        f"{product.get('name')}: {e}"
                    )
                    vk_failed += 1

            await callback.message.answer(
                f"📘 ВКонтакте:\n"
                f"✅ Опубликовано: {vk_success} товаров\n"
                f"❌ Ошибок: {vk_failed}"
            )

        await callback.message.answer(
            f"🎉 Готово! Все товары обработаны и опубликованы на {platform}."
        )

    except Exception as e:
        logger.error(f"Ошибка выгрузки: {e}")
        await callback.message.answer(
            f"⚠️ Ошибка при выгрузке: {str(e)}"
        )


@router.callback_query(lambda c: c.data == "upload_stop")
async def upload_stop(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer("⏹ Выгрузка остановлена.")
