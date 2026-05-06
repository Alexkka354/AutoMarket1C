import logging
import traceback

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

from avito.auth import get_access_token
from avito.client import (
    get_autoload_profile,
    update_autoload_profile,
    trigger_upload,
    get_last_report,
    get_report_items,
    get_categories_tree,
)
from avito.feed import generate_feed, generate_single_ad_feed
from content.generator import generate_title, generate_description
from content.image_search import search_product_image

logger = logging.getLogger(__name__)
router = Router()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ───────────────── FSM ─────────────────


class AvitoState(StatesGroup):
    waiting_for_product = State()
    waiting_for_price = State()
    waiting_for_photo = State()
    waiting_for_photo_confirm = State()
    waiting_for_feed_url = State()


# ───────────────── Клавиатуры ─────────────────


def avito_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Опубликовать товар",
            callback_data="avito_publish",
        )],
        [InlineKeyboardButton(
            text="Выгрузить все товары (XML-фид)",
            callback_data="avito_bulk_upload",
        )],
        [InlineKeyboardButton(
            text="Статус автозагрузки",
            callback_data="avito_status",
        )],
        [InlineKeyboardButton(
            text="Последний отчёт",
            callback_data="avito_last_report",
        )],
        [InlineKeyboardButton(
            text="Настроить профиль автозагрузки",
            callback_data="avito_setup_profile",
        )],
        [InlineKeyboardButton(
            text="Назад в меню",
            callback_data="back_to_menu",
        )],
    ])


def photo_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Найти фото автоматически",
            callback_data="avito_auto_photo",
        )],
        [InlineKeyboardButton(
            text="Пропустить (без фото)",
            callback_data="avito_skip_photo",
        )],
    ])


def photo_confirm_keyboard(idx: int, total: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text="Использовать это фото",
            callback_data="avito_confirm_photo",
        )],
    ]
    if idx + 1 < total:
        rows.append([InlineKeyboardButton(
            text=f"Следующее фото ({idx + 1}/{total})",
            callback_data="avito_next_photo",
        )])
    rows.append([InlineKeyboardButton(
        text="Опубликовать без фото",
        callback_data="avito_skip_photo",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ───────────────── Меню Авито ─────────────────


@router.callback_query(lambda c: c.data == "avito_menu")
async def avito_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Авито — выберите действие:",
        reply_markup=avito_menu_keyboard(),
    )


# ───────────────── Публикация одного товара ─────────────────


@router.callback_query(lambda c: c.data == "avito_publish")
async def start_avito_publish(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Публикация товара на Авито\n\n"
        "Введите название и характеристики товара:"
    )
    await state.set_state(AvitoState.waiting_for_product)


@router.message(AvitoState.waiting_for_product)
async def process_avito_product(message: Message, state: FSMContext):
    await state.update_data(product=message.text)
    await message.answer("Введите цену товара в рублях (например: 5000):")
    await state.set_state(AvitoState.waiting_for_price)


@router.message(AvitoState.waiting_for_price)
async def process_avito_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число, например: 5000")
        return
    await state.update_data(price=float(message.text))
    await message.answer(
        "Отправьте фото товара прямо в чат\nили выберите действие:",
        reply_markup=photo_choice_keyboard(),
    )
    await state.set_state(AvitoState.waiting_for_photo)


# --- Пользователь отправил своё фото ---


@router.message(AvitoState.waiting_for_photo, F.photo)
async def process_avito_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    photo_url = (
        f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
    )
    await state.update_data(photo_url=photo_url, photo_bytes=None)
    await _publish_to_avito(message, state)


# --- Кнопка "Найти фото автоматически" ---


@router.callback_query(lambda c: c.data == "avito_auto_photo")
async def avito_auto_search_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    product_name = data.get("product", "")

    await callback.message.answer(
        f"Ищу фото по запросу: {product_name}..."
    )

    result = await search_product_image(product_name, max_results=10)
    urls = result["urls"]

    if not urls:
        await callback.message.answer(
            "Не удалось найти фото в интернете.\n\n"
            "Отправьте своё фото или нажмите 'Пропустить':",
            reply_markup=photo_choice_keyboard(),
        )
        return

    await state.update_data(auto_photos=urls, auto_photo_idx=0)
    await _show_photo_candidate(callback.message, state, urls, 0)


async def _download_image(url: str) -> bytes | None:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status != 200:
                    return None
                return await resp.read()
    except Exception:
        return None


async def _show_photo_candidate(
    message: Message,
    state: FSMContext,
    urls: list[str],
    idx: int,
):
    photo_data = await _download_image(urls[idx])
    if photo_data:
        buf = BufferedInputFile(photo_data, filename=f"photo_{idx}.jpg")
        await message.answer_photo(
            buf,
            caption=f"Фото {idx + 1} из {len(urls)}. Использовать?",
            reply_markup=photo_confirm_keyboard(idx, len(urls)),
        )
        await state.update_data(current_photo_bytes=photo_data)
    else:
        if idx + 1 < len(urls):
            await state.update_data(auto_photo_idx=idx + 1)
            await _show_photo_candidate(message, state, urls, idx + 1)
        else:
            await message.answer(
                "Не удалось загрузить фото.\n"
                "Отправьте своё или нажмите 'Пропустить':",
                reply_markup=photo_choice_keyboard(),
            )
    await state.set_state(AvitoState.waiting_for_photo_confirm)


@router.callback_query(lambda c: c.data == "avito_next_photo")
async def avito_next_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    urls = data.get("auto_photos", [])
    idx = data.get("auto_photo_idx", 0) + 1

    if idx >= len(urls):
        await callback.message.answer(
            "Больше фото нет. Отправьте своё или пропустите:",
            reply_markup=photo_choice_keyboard(),
        )
        await state.set_state(AvitoState.waiting_for_photo)
        return

    await state.update_data(auto_photo_idx=idx)
    await _show_photo_candidate(callback.message, state, urls, idx)


@router.callback_query(lambda c: c.data == "avito_confirm_photo")
async def avito_confirm_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    photo_bytes = data.get("current_photo_bytes")
    if photo_bytes:
        await state.update_data(photo_bytes=photo_bytes, photo_url=None)
    await _publish_to_avito(callback.message, state)


@router.callback_query(lambda c: c.data == "avito_skip_photo")
async def avito_skip_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(photo_url=None, photo_bytes=None)
    await _publish_to_avito(callback.message, state)


# ───────────────── Генерация и публикация ─────────────────


async def _publish_to_avito(message: Message, state: FSMContext):
    data = await state.get_data()
    product_name = data.get("product", "")
    price = data.get("price", 0)
    photo_url = data.get("photo_url")

    await message.answer("Генерирую заголовок и описание с помощью ИИ...")

    try:
        title = await generate_title(product_name, "")
    except Exception:
        title = product_name

    try:
        description = await generate_description(product_name, "", "Авито")
    except Exception:
        description = product_name

    if len(title) > 50:
        title = title[:50]

    await message.answer(
        f"Заголовок: {title}\n"
        f"Описание: {description}\n"
        f"Цена: {int(price)} руб.\n\n"
        "Генерирую XML-фид для Авито..."
    )

    xml_content = generate_single_ad_feed(
        ad_id=f"bot_{int(price)}_{hash(product_name) % 100000}",
        title=title,
        description=description,
        price=price,
        image_url=photo_url,
    )

    xml_file = BufferedInputFile(
        xml_content.encode("utf-8"),
        filename="avito_ad.xml",
    )
    await message.answer_document(
        xml_file,
        caption=(
            "XML-фид для объявления на Авито готов!\n\n"
            "Чтобы опубликовать:\n"
            "1. Разместите этот файл на публичном URL\n"
            "2. Укажите URL в профиле автозагрузки\n"
            "3. Запустите выгрузку через кнопку 'Статус автозагрузки'"
        ),
    )

    await state.clear()
    await message.answer(
        "Выберите следующее действие:",
        reply_markup=avito_menu_keyboard(),
    )


# ───────────────── Массовая выгрузка (XML-фид из БД) ─────────────────


@router.callback_query(lambda c: c.data == "avito_bulk_upload")
async def avito_bulk_upload(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Загружаю список товаров из базы данных...")

    try:
        from integration_module.client import get_products
        products = await get_products()
    except Exception:
        products = []

    if not products:
        await callback.message.answer(
            "В базе нет товаров.\n"
            "Сначала выполните синхронизацию с 1С через 'Запустить выгрузку'.",
            reply_markup=avito_menu_keyboard(),
        )
        return

    xml_content = generate_feed(products)
    xml_file = BufferedInputFile(
        xml_content.encode("utf-8"),
        filename="avito_feed.xml",
    )
    await callback.message.answer_document(
        xml_file,
        caption=(
            f"XML-фид для Авито готов ({len(products)} товаров).\n\n"
            "Разместите файл на публичном URL и настройте профиль автозагрузки."
        ),
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=avito_menu_keyboard(),
    )


# ───────────────── Статус автозагрузки ─────────────────


@router.callback_query(lambda c: c.data == "avito_status")
async def avito_status(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Проверяю подключение к API Авито...")

    try:
        token = await get_access_token()
        await callback.message.answer(
            "Авторизация: Успешно\n"
            f"Токен получен (первые 10 символов): {token[:10]}...\n\n"
            "Загружаю профиль автозагрузки..."
        )
    except Exception as e:
        await callback.message.answer(
            f"Ошибка авторизации: {e}\n\n"
            "Проверьте AVITO_CLIENT_ID и AVITO_CLIENT_SECRET в .env"
        )
        return

    try:
        profile = await get_autoload_profile()
        enabled = profile.get("autoload_enabled", False)
        feeds = profile.get("feeds_data", [])
        email = profile.get("report_email", "не указан")

        feeds_text = "\n".join(
            f"  - {f.get('url', 'N/A')}" for f in feeds
        ) if feeds else "  не настроены"

        await callback.message.answer(
            f"Профиль автозагрузки\n\n"
            f"Статус: {'Включена' if enabled else 'Выключена'}\n"
            f"Фиды:\n{feeds_text}\n"
            f"Email для отчётов: {email}",
            reply_markup=avito_menu_keyboard(),
        )
    except Exception as e:
        await callback.message.answer(
            f"Не удалось загрузить профиль: {e}\n"
            "Возможно, профиль автозагрузки ещё не создан.",
            reply_markup=avito_menu_keyboard(),
        )


# ───────────────── Последний отчёт ─────────────────


@router.callback_query(lambda c: c.data == "avito_last_report")
async def avito_last_report(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Загружаю последний отчёт автозагрузки...")

    try:
        report = await get_last_report()
        report_id = report.get("report_id", "N/A")
        status = report.get("status", "N/A")
        started = report.get("started_at", "N/A")
        finished = report.get("finished_at", "N/A")
        source = report.get("source", "N/A")

        stats = report.get("section_stats", {})
        total = stats.get("count", 0)

        await callback.message.answer(
            f"Последний отчёт автозагрузки\n\n"
            f"ID отчёта: {report_id}\n"
            f"Статус: {status}\n"
            f"Источник: {source}\n"
            f"Начало: {started}\n"
            f"Окончание: {finished}\n"
            f"Всего объявлений: {total}",
            reply_markup=avito_menu_keyboard(),
        )
    except Exception as e:
        await callback.message.answer(
            f"Не удалось загрузить отчёт: {e}",
            reply_markup=avito_menu_keyboard(),
        )


# ───────────────── Настройка профиля ─────────────────


@router.callback_query(lambda c: c.data == "avito_setup_profile")
async def avito_setup_profile(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Введите URL вашего XML-фида для автозагрузки\n"
        "(файл должен быть доступен по HTTPS):"
    )
    await state.set_state(AvitoState.waiting_for_feed_url)


@router.message(AvitoState.waiting_for_feed_url)
async def process_feed_url(message: Message, state: FSMContext):
    feed_url = message.text.strip()
    if not feed_url.startswith("http"):
        await message.answer("URL должен начинаться с http:// или https://")
        return

    await message.answer(f"Настраиваю профиль автозагрузки...\nURL фида: {feed_url}")

    try:
        await update_autoload_profile(feed_url=feed_url)
        await message.answer(
            "Профиль автозагрузки обновлён!\n\n"
            f"URL фида: {feed_url}\n"
            "Автозагрузка включена.\n\n"
            "Теперь Авито будет загружать объявления из этого файла.",
            reply_markup=avito_menu_keyboard(),
        )
    except Exception as e:
        logger.error("Ошибка обновления профиля: %s\n%s", e, traceback.format_exc())
        await message.answer(
            f"Ошибка настройки профиля: {e}",
            reply_markup=avito_menu_keyboard(),
        )

    await state.clear()
