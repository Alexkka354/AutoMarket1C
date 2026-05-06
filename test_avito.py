"""
Тестовый скрипт для проверки модуля публикации на Авито.
Запускается без Telegram-бота, прямо из консоли.

Использование:
    python test_avito.py

Что делает:
    1. Проверяет авторизацию (получение access_token)
    2. Генерирует XML-фид для тестового товара
    3. Сохраняет XML-фид в файл avito_test_feed.xml
    4. (опционально) Загружает профиль автозагрузки
    5. (опционально) Получает дерево категорий Авито
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()


async def test_auth():
    """Тест 1: Проверка авторизации в API Авито."""
    print("=" * 60)
    print("ТЕСТ 1: Авторизация (получение access_token)")
    print("=" * 60)

    from avito.auth import get_access_token

    try:
        token = await get_access_token()
        print(f"  Статус: УСПЕШНО")
        print(f"  Токен (первые 20 символов): {token[:20]}...")
        print(f"  Длина токена: {len(token)} символов")
        return True
    except Exception as e:
        print(f"  Статус: ОШИБКА")
        print(f"  Причина: {e}")
        print()
        print("  Проверьте что в файле .env указаны правильные значения:")
        print("    AVITO_CLIENT_ID=ваш_client_id")
        print("    AVITO_CLIENT_SECRET=ваш_client_secret")
        return False


async def test_feed_generation():
    """Тест 2: Генерация XML-фида для тестового товара."""
    print()
    print("=" * 60)
    print("ТЕСТ 2: Генерация XML-фида")
    print("=" * 60)

    from avito.feed import generate_feed, generate_single_ad_feed

    # --- Тест 2а: Один товар ---
    print()
    print("  2a. Генерация фида для одного товара...")

    xml_single = generate_single_ad_feed(
        ad_id="TEST-001",
        title="Смартфон Samsung Galaxy A54",
        description="Новый смартфон Samsung Galaxy A54 8/256 ГБ. "
                    "Экран Super AMOLED 6.4 дюйма, тройная камера 50 МП, "
                    "аккумулятор 5000 мАч. Гарантия 1 год.",
        price=25990,
        category="Телефоны",
        image_url="https://example.com/photo.jpg",
    )

    filename_single = "avito_test_single.xml"
    with open(filename_single, "w", encoding="utf-8") as f:
        f.write(xml_single)

    print(f"  Статус: УСПЕШНО")
    print(f"  Файл сохранён: {filename_single}")
    print()
    print("  Содержимое XML:")
    print("  " + "-" * 50)
    for line in xml_single.strip().split("\n"):
        print(f"  {line}")
    print("  " + "-" * 50)

    # --- Тест 2б: Несколько товаров (имитация БД) ---
    print()
    print("  2b. Генерация фида для нескольких товаров...")

    test_products = [
        {
            "article": "ART-001",
            "name": "Наушники Sony WH-1000XM5",
            "description": "Беспроводные наушники с шумоподавлением. "
                           "Bluetooth 5.2, время работы до 30 часов.",
            "price": 28990,
            "category": "Аудио и видео",
            "image_url": "https://example.com/sony.jpg",
            "stock": 5,
        },
        {
            "article": "ART-002",
            "name": "Ноутбук ASUS VivoBook 15",
            "description": "Ноутбук для работы и учёбы. Intel Core i5, "
                           "8 ГБ RAM, SSD 512 ГБ, экран 15.6 дюймов.",
            "price": 45990,
            "category": "Ноутбуки",
            "image_url": "https://example.com/asus.jpg",
            "stock": 3,
        },
        {
            "article": "ART-003",
            "name": "Робот-пылесос Xiaomi",
            "description": "Робот-пылесос с влажной уборкой. "
                           "Мощность всасывания 4000 Па, навигация LiDAR.",
            "price": 19990,
            "category": "Товары для дома",
            "stock": 10,
        },
    ]

    xml_bulk = generate_feed(test_products)

    filename_bulk = "avito_test_feed.xml"
    with open(filename_bulk, "w", encoding="utf-8") as f:
        f.write(xml_bulk)

    print(f"  Статус: УСПЕШНО")
    print(f"  Товаров в фиде: {len(test_products)}")
    print(f"  Файл сохранён: {filename_bulk}")
    print()
    print("  Содержимое XML:")
    print("  " + "-" * 50)
    for line in xml_bulk.strip().split("\n"):
        print(f"  {line}")
    print("  " + "-" * 50)

    return True


async def test_profile():
    """Тест 3: Получение профиля автозагрузки (требует авторизацию)."""
    print()
    print("=" * 60)
    print("ТЕСТ 3: Профиль автозагрузки")
    print("=" * 60)

    from avito.client import get_autoload_profile

    try:
        profile = await get_autoload_profile()
        enabled = profile.get("autoload_enabled", False)
        feeds = profile.get("feeds_data", [])
        email = profile.get("report_email", "не указан")

        print(f"  Статус: УСПЕШНО")
        print(f"  Автозагрузка: {'Включена' if enabled else 'Выключена'}")
        print(f"  Email для отчётов: {email}")

        if feeds:
            print(f"  Фиды:")
            for f in feeds:
                print(f"    - {f.get('url', 'N/A')}")
        else:
            print(f"  Фиды: не настроены")

        return True
    except Exception as e:
        print(f"  Статус: ОШИБКА (это нормально если профиль ещё не создан)")
        print(f"  Причина: {e}")
        return False


async def test_categories():
    """Тест 4: Получение дерева категорий Авито."""
    print()
    print("=" * 60)
    print("ТЕСТ 4: Дерево категорий Авито")
    print("=" * 60)

    from avito.client import get_categories_tree

    try:
        tree = await get_categories_tree()
        categories = tree.get("categories", [])
        print(f"  Статус: УСПЕШНО")
        print(f"  Всего категорий верхнего уровня: {len(categories)}")

        if categories:
            print(f"  Первые 10 категорий:")
            for cat in categories[:10]:
                name = cat.get("name", "N/A")
                slug = cat.get("slug", "N/A")
                print(f"    - {name} (slug: {slug})")

        return True
    except Exception as e:
        print(f"  Статус: ОШИБКА")
        print(f"  Причина: {e}")
        return False


async def main():
    print()
    print("*" * 60)
    print("  ТЕСТИРОВАНИЕ МОДУЛЯ ПУБЛИКАЦИИ НА АВИТО")
    print("*" * 60)
    print()

    # Тест 1: Авторизация
    auth_ok = await test_auth()

    # Тест 2: Генерация XML-фида (работает без авторизации)
    feed_ok = await test_feed_generation()

    # Тесты 3 и 4 требуют успешной авторизации
    if auth_ok:
        await test_profile()
        await test_categories()
    else:
        print()
        print("  Тесты 3 и 4 пропущены (требуется авторизация)")

    # Итог
    print()
    print("=" * 60)
    print("  ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"  Авторизация:     {'OK' if auth_ok else 'ОШИБКА (проверьте .env)'}")
    print(f"  Генерация фида:  {'OK' if feed_ok else 'ОШИБКА'}")
    print()

    if feed_ok:
        print("  Сгенерированные файлы:")
        print("    - avito_test_single.xml  (один товар)")
        print("    - avito_test_feed.xml    (несколько товаров)")
        print()
        print("  Эти файлы можно:")
        print("    1. Открыть и посмотреть структуру XML")
        print("    2. Загрузить на любой хостинг по HTTPS")
        print("    3. Указать URL в профиле автозагрузки Авито")


if __name__ == "__main__":
    asyncio.run(main())
