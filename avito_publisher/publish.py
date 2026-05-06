"""
Главный скрипт публикации объявлений на Авито.

Запуск:
    python -m avito_publisher.publish

Что делает:
    1. Авторизуется в API Авито (OAuth2 client_credentials)
    2. Генерирует XML-фид из данных о товарах
    3. Сохраняет XML в файл
    4. Настраивает профиль автозагрузки (указывает URL фида)
    5. Запускает выгрузку объявлений
    6. Проверяет статус выгрузки

Для работы нужно:
    - Указать AVITO_CLIENT_ID и AVITO_CLIENT_SECRET в файле .env
    - Указать FEED_URL — публичный URL, где будет размещён XML-фид
    - Заполнить список товаров в переменной PRODUCTS ниже
"""

import asyncio
import sys
import os

# Добавляем родительскую папку в sys.path, чтобы можно было
# запускать скрипт как из папки avito_publisher, так и из корня проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avito_publisher.auth import get_access_token
from avito_publisher.client import (
    get_autoload_profile,
    setup_autoload_profile,
    trigger_upload,
    get_last_report,
    get_categories,
)
from avito_publisher.feed import generate_feed, save_feed


# =====================================================================
#  ДАННЫЕ ДЛЯ ОБЪЯВЛЕНИЙ — ЗАПОЛНИТЕ СВОИМИ ТОВАРАМИ
# =====================================================================

PRODUCTS = [
    {
        "id": "AUTO-001",
        "title": "Смартфон Samsung Galaxy A54",
        "description": (
            "Новый смартфон Samsung Galaxy A54 8/256 ГБ, чёрный цвет.\n"
            "Экран Super AMOLED 6.4 дюйма, разрешение 2340x1080.\n"
            "Тройная камера 50+12+5 МП.\n"
            "Аккумулятор 5000 мАч, быстрая зарядка 25 Вт.\n"
            "Гарантия 1 год от производителя."
        ),
        "price": 25990,
        "category": "Телефоны",
        "condition": "Новое",
        "image_urls": [
            "https://example.com/photos/samsung_a54_front.jpg",
            "https://example.com/photos/samsung_a54_back.jpg",
        ],
        "address": "Москва, ул. Примерная, д. 1",
        "contact_phone": "+79001234567",
    },
    {
        "id": "AUTO-002",
        "title": "Наушники Sony WH-1000XM5",
        "description": (
            "Беспроводные наушники Sony WH-1000XM5 с активным шумоподавлением.\n"
            "Bluetooth 5.2, кодеки LDAC, AAC.\n"
            "Время работы до 30 часов от одного заряда.\n"
            "В комплекте: наушники, кабель USB-C, чехол, аудиокабель 3.5 мм."
        ),
        "price": 28990,
        "category": "Аудио и видео",
        "condition": "Новое",
        "image_url": "https://example.com/photos/sony_xm5.jpg",
    },
    {
        "id": "AUTO-003",
        "title": "Робот-пылесос Xiaomi X10+",
        "description": (
            "Робот-пылесос Xiaomi X10+ с функцией влажной уборки.\n"
            "Мощность всасывания 4000 Па.\n"
            "Навигация LiDAR, построение карты помещения.\n"
            "Самоочистка на станции, объём пылесборника 2.5 л.\n"
            "Управление через приложение Mi Home."
        ),
        "price": 32990,
        "category": "Товары для дома",
        "condition": "Новое",
    },
]

# URL, по которому будет доступен ваш XML-фид (HTTPS обязательно)
# Замените на реальный URL вашего сервера
FEED_URL = "https://ваш-сервер.ru/avito_feed.xml"

# Имя XML-файла для сохранения
OUTPUT_FILE = "avito_feed.xml"


# =====================================================================
#  ОСНОВНЫЕ ФУНКЦИИ
# =====================================================================


async def step1_check_auth():
    """Шаг 1: Проверка авторизации."""
    print("=" * 60)
    print("  ШАГ 1: Авторизация в API Авито")
    print("=" * 60)

    try:
        token = await get_access_token()
        print(f"  Результат: УСПЕШНО")
        print(f"  Токен: {token[:20]}...")
        return True
    except Exception as e:
        print(f"  Результат: ОШИБКА")
        print(f"  {e}")
        print()
        print("  Проверьте файл .env:")
        print("    AVITO_CLIENT_ID=ваш_client_id")
        print("    AVITO_CLIENT_SECRET=ваш_client_secret")
        return False


async def step2_generate_feed():
    """Шаг 2: Генерация XML-фида."""
    print()
    print("=" * 60)
    print("  ШАГ 2: Генерация XML-фида")
    print("=" * 60)

    filepath = save_feed(PRODUCTS, filename=OUTPUT_FILE)
    print(f"  Товаров в фиде: {len(PRODUCTS)}")
    print(f"  Файл сохранён: {filepath}")

    # Показать содержимое
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    print()
    print("  Содержимое XML-фида:")
    print("  " + "-" * 50)
    for line in content.strip().split("\n"):
        print(f"  {line}")
    print("  " + "-" * 50)

    return True


async def step3_setup_profile():
    """Шаг 3: Настройка профиля автозагрузки."""
    print()
    print("=" * 60)
    print("  ШАГ 3: Настройка профиля автозагрузки")
    print("=" * 60)

    if FEED_URL.startswith("https://ваш"):
        print("  ПРОПУЩЕНО: укажите реальный FEED_URL в скрипте")
        print(f"  Текущее значение: {FEED_URL}")
        print()
        print("  Чтобы настроить профиль:")
        print("  1. Разместите файл avito_feed.xml на HTTPS-сервере")
        print("  2. Замените FEED_URL в этом скрипте на реальный URL")
        print("  3. Запустите скрипт заново")
        return False

    print(f"  URL фида: {FEED_URL}")

    try:
        await setup_autoload_profile(feed_url=FEED_URL)
        print(f"  Результат: ПРОФИЛЬ ОБНОВЛЁН")
        print(f"  Автозагрузка включена")
        return True
    except Exception as e:
        print(f"  Результат: ОШИБКА")
        print(f"  {e}")
        return False


async def step4_trigger_upload():
    """Шаг 4: Запуск выгрузки."""
    print()
    print("=" * 60)
    print("  ШАГ 4: Запуск выгрузки")
    print("=" * 60)

    if FEED_URL.startswith("https://ваш"):
        print("  ПРОПУЩЕНО: сначала настройте FEED_URL (шаг 3)")
        return False

    try:
        result = await trigger_upload()
        print(f"  Результат: ВЫГРУЗКА ЗАПУЩЕНА")
        print(f"  Ответ API: {result}")
        return True
    except Exception as e:
        print(f"  Результат: ОШИБКА")
        print(f"  {e}")
        print()
        print("  Возможные причины:")
        print("  - Выгрузка уже запускалась менее часа назад")
        print("  - Профиль автозагрузки не настроен")
        return False


async def step5_check_status():
    """Шаг 5: Проверка статуса."""
    print()
    print("=" * 60)
    print("  ШАГ 5: Проверка статуса")
    print("=" * 60)

    # Профиль
    try:
        profile = await get_autoload_profile()
        enabled = profile.get("autoload_enabled", False)
        feeds = profile.get("feeds_data", [])
        print(f"  Автозагрузка: {'включена' if enabled else 'выключена'}")
        if feeds:
            for f in feeds:
                print(f"  Фид: {f.get('url', 'N/A')}")
        else:
            print(f"  Фиды: не настроены")
    except Exception as e:
        print(f"  Профиль: не удалось загрузить ({e})")

    # Последний отчёт
    try:
        report = await get_last_report()
        print(f"  Последний отчёт: ID={report.get('report_id')}, "
              f"статус={report.get('status')}")
    except Exception:
        print(f"  Последний отчёт: нет данных")


async def main():
    print()
    print("*" * 60)
    print("  ПУБЛИКАЦИЯ ОБЪЯВЛЕНИЙ НА АВИТО")
    print("*" * 60)
    print()

    # Шаг 1: Авторизация
    auth_ok = await step1_check_auth()
    if not auth_ok:
        print()
        print("Авторизация не прошла. Исправьте ошибки и запустите заново.")
        print("XML-фид всё равно будет сгенерирован (шаг 2).")

    # Шаг 2: Генерация фида (работает без авторизации)
    await step2_generate_feed()

    if not auth_ok:
        print()
        print("Шаги 3-5 пропущены (нет авторизации).")
        return

    # Шаг 3: Настройка профиля
    profile_ok = await step3_setup_profile()

    # Шаг 4: Запуск выгрузки
    if profile_ok:
        await step4_trigger_upload()

    # Шаг 5: Проверка статуса
    await step5_check_status()

    # Итог
    print()
    print("=" * 60)
    print("  ГОТОВО")
    print("=" * 60)
    print(f"  XML-фид сохранён в файл: {OUTPUT_FILE}")
    print(f"  Товаров в фиде: {len(PRODUCTS)}")
    if profile_ok:
        print(f"  Профиль автозагрузки настроен: {FEED_URL}")
    else:
        print(f"  Следующий шаг: разместите {OUTPUT_FILE} на HTTPS-сервере")
        print(f"  и укажите URL в переменной FEED_URL в этом скрипте")


if __name__ == "__main__":
    asyncio.run(main())
