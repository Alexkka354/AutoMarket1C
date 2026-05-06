"""
Модуль поиска фото товара по названию.
Использует Yandex Картинки (поиск в интернете) для поиска
реальных фотографий товаров — телефонов, наушников и т.д.

Не требует API-ключа, работает из России без VPN.
"""

import aiohttp
import html
import re
from urllib.parse import quote_plus

YANDEX_URL = "https://yandex.ru/images/search"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Регулярка вытаскивает прямые ссылки на изображения из HTML Яндекс.Картинок
_IMG_PATTERN = re.compile(
    r'"img_href":"(https?://[^"]+?\.(?:jpg|jpeg|png|webp))"',
    re.IGNORECASE,
)


async def search_yandex_images(query: str, max_results: int = 10) -> list[str]:
    """
    Ищет фото в Яндекс.Картинках по запросу.
    Возвращает список прямых URL изображений (от 0 до max_results штук).
    """
    params = {"text": query, "from": "tabbar"}
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                YANDEX_URL, params=params, headers=headers, timeout=15
            ) as resp:
                if resp.status != 200:
                    print(f"⚠ Yandex вернул статус {resp.status}")
                    return []
                html_text = await resp.text()
    except Exception as e:
        print(f"⚠ Ошибка запроса к Yandex: {e}")
        return []

    # Декодируем HTML-сущности (&quot; -> ", &amp; -> & и т.д.)
    decoded = html.unescape(html_text)

    matches = _IMG_PATTERN.findall(decoded)

    # Убираем дубликаты, сохраняя порядок
    seen = set()
    results = []
    for url in matches:
        if url not in seen:
            seen.add(url)
            results.append(url)
        if len(results) >= max_results:
            break

    return results


async def search_product_image(product_name: str, max_results: int = 5) -> dict:
    """
    Главная функция модуля.
    Ищет фото товара через Яндекс.Картинки.

    Возвращает словарь:
    {
        "urls": ["https://...", ...],   # список найденных фото
        "query_used": "Samsung Galaxy A54",
        "source": "yandex.ru/images"
    }
    """
    print(f"🔍 Ищу фото в Яндекс.Картинках: {product_name}")

    urls = await search_yandex_images(product_name, max_results=max_results)

    return {
        "urls": urls,
        "query_used": product_name,
        "source": "yandex.ru/images",
    }
