import aiohttp
from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from vk.market import add_product, get_products
from content.generator import generate_title, generate_description
from content.image_search import search_product_image

router = Router()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class VKState(StatesGroup):
    waiting_for_product = State()
    waiting_for_price = State()
    waiting_for_photo = State()
    waiting_for_photo_confirm = State()


def photo_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔍 Найти фото автоматически (поиск в интернете)",
            callback_data="vk_auto_photo",
        )],
        [InlineKeyboardButton(
            text="⏩ Пропустить (без фото)",
            callback_data="vk_skip_photo",
        )],
    ])


def photo_confirm_keyboard(idx: int, total: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text="✅ Использовать это фото",
            callback_data="vk_confirm_photo",
        )],
    ]
    if idx + 1 < total:
        rows.append([InlineKeyboardButton(
            text=f"➡ Следующее фото ({idx + 1}/{total})",
            callback_data="vk_next_photo",
        )])
    rows.append([InlineKeyboardButton(
        text="⏩ Опубликовать без фото",
        callback_data="vk_skip_photo",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _download_image(url: str) -> bytes | None:
    """Скачивает изображение с браузерным User-Agent.
    Возвращает байты или None при ошибке.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status != 200:
                    print(f"⚠ {url} вернул {resp.status}")
                    return None
                return await resp.read()
    except Exception as e:
        print(f"⚠ Ошибка скачивания {url}: {e}")
        return None


# ─────────────────── Публикация товара ───────────────────


@router.callback_query(lambda c: c.data == "vk_publish")
async def start_vk_publish(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📘 Публикация товара ВКонтакте\n\n"
        "Введите название и характеристики товара:"
    )
    await state.set_state(VKState.waiting_for_product)


@router.message(VKState.waiting_for_product)
async def process_vk_product(message: Message, state: FSMContext):
    await state.update_data(product=message.text)
    await message.answer("💰 Введите цену товара в рублях (например: 5000):")
    await state.set_state(VKState.waiting_for_price)


@router.message(VKState.waiting_for_price)
async def process_vk_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число, например: 5000")
        return
    await state.update_data(price=float(message.text))
    await message.answer(
        "📷 Отправьте фото товара прямо в чат\n"
        "или выберите действие:",
        reply_markup=photo_choice_keyboard(),
    )
    await state.set_state(VKState.waiting_for_photo)


# --- Пользователь отправил своё фото ---


@router.message(VKState.waiting_for_photo, F.photo)
async def process_vk_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
    await state.update_data(photo_url=photo_url, photo_bytes=None)
    await publish_to_vk(message, state)


# --- Кнопка "Найти фото автоматически" ---


@router.callback_query(lambda c: c.data == "vk_auto_photo")
async def auto_search_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    product_name = data.get("product", "")

    await callback.message.answer(
        f"🔍 Ищу фото в Яндекс.Картинках по запросу: {product_name}..."
    )

    result = await search_product_image(product_name, max_results=10)
    urls = result["urls"]

    if not urls:
        await callback.message.answer(
            "😔 Не удалось найти фото в интернете.\n\n"
            "Отправьте своё фото или нажмите «Пропустить»:",
            reply_markup=photo_choice_keyboard(),
        )
        return

    await state.update_data(auto_photos=urls, auto_photo_idx=0)
    await _send_photo_preview(callback.message, state)


async def _send_photo_preview(message: Message, state: FSMContext):
    """Скачивает фото к боту и отправляет превью пользователю.
    Если фото не скачивается — пропускает и пробует следующее.
    """
    data = await state.get_data()
    urls = data.get("auto_photos", [])
    idx = data.get("auto_photo_idx", 0)

    # Перебираем варианты пока не найдём рабочий
    while idx < len(urls):
        current_url = urls[idx]
        photo_bytes = await _download_image(current_url)

        if photo_bytes is None:
            # Не удалось скачать — пробуем следующее
            idx += 1
            continue

        # Сохраняем байты и URL в состоянии — потом передадим в VK
        await state.update_data(
            photo_url=current_url,
            photo_bytes=photo_bytes,
            auto_photo_idx=idx,
        )

        try:
            input_file = BufferedInputFile(
                photo_bytes, filename=f"product_{idx}.jpg"
            )
            await message.answer_photo(
                photo=input_file,
                caption=(
                    f"📷 Вариант {idx + 1} из {len(urls)}\n"
                    f"🔗 Источник: Яндекс.Картинки\n\n"
                    f"Использовать это фото?"
                ),
                reply_markup=photo_confirm_keyboard(idx, len(urls)),
            )
            await state.set_state(VKState.waiting_for_photo_confirm)
            return
        except Exception as e:
            print(f"⚠ Telegram отверг фото {current_url}: {e}")
            idx += 1
            continue

    # Все варианты перебрали — ничего не подошло
    await message.answer(
        "😔 Все найденные фото не удалось загрузить.\n\n"
        "Отправьте своё фото или нажмите «Пропустить»:",
        reply_markup=photo_choice_keyboard(),
    )
    await state.update_data(photo_url=None, photo_bytes=None)
    await state.set_state(VKState.waiting_for_photo)


@router.callback_query(lambda c: c.data == "vk_next_photo")
async def next_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    idx = data.get("auto_photo_idx", 0)
    await state.update_data(auto_photo_idx=idx + 1)
    await _send_photo_preview(callback.message, state)


@router.callback_query(lambda c: c.data == "vk_confirm_photo")
async def confirm_found_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Публикую товар...")
    await publish_to_vk(callback.message, state)


@router.callback_query(lambda c: c.data == "vk_skip_photo")
async def skip_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(photo_url=None, photo_bytes=None)
    await publish_to_vk(callback.message, state)


# ─────────────────── Публикация в VK ───────────────────


async def publish_to_vk(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    product = data["product"]
    price = data["price"]
    photo_url = data.get("photo_url")
    photo_bytes = data.get("photo_bytes")

    await message.answer("⏳ Генерирую контент и публикую товар...")

    try:
        title = await generate_title(product, product)
        description = await generate_description(product, product, "ВКонтакте")
        # Если есть скачанные байты — передаём их (надёжнее, обходит блокировку хотлинков)
        # Иначе передаём URL — vk/market.py сам скачает (как раньше)
        result = await add_product(
            title, description, price, photo_bytes or photo_url
        )

        if "response" in result:
            item_id = result["response"]["market_item_id"]
            photo_status = "✅ С фото" if (photo_url or photo_bytes) else "❌ Без фото"
            await message.answer(
                f"✅ Товар опубликован ВКонтакте!\n\n"
                f"📌 Заголовок: {title}\n"
                f"💰 Цена: {price} руб.\n"
                f"📷 Фото: {photo_status}\n"
                f"🆔 ID товара: {item_id}"
            )
        else:
            error = result.get("error", {}).get("error_msg", "Неизвестная ошибка")
            await message.answer(f"❌ Ошибка публикации: {error}")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


# ─────────────────── Список товаров ───────────────────


@router.callback_query(lambda c: c.data == "vk_products")
async def show_vk_products(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("⏳ Загружаю список товаров...")
    try:
        result = await get_products()
        if "response" in result:
            items = result["response"]["items"]
            if not items:
                await callback.message.answer("📭 Товаров пока нет.")
                return
            text = "📦 Товары ВКонтакте:\n\n"
            for item in items[:10]:
                text += (
                    f"• {item['title']} — "
                    f"{item['price']['amount'] // 100} руб.\n"
                )
            await callback.message.answer(text)
        else:
            error = result.get("error", {}).get("error_msg", "Неизвестная ошибка")
            await callback.message.answer(f"❌ Ошибка: {error}")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
