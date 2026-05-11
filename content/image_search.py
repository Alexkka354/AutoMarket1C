"""
Модуль поиска фото товара по названию.

Использует Yandex Картинки для поиска кандидатов-изображений,
затем ранжирует их через модель CLIP ViT-B/32 и отбирает лучшее
по итоговому ранговому баллу R(I).

Не требует API-ключа, работает из России без VPN.
"""

import aiohttp
import html
import re
import logging
from urllib.parse import quote_plus

from content.clip_ranker import (
    get_clip_ranker,
    R_THRESHOLD,
    R_VERIFICATION_ZONE,
)

logger = logging.getLogger(__name__)

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
                    logger.warning("Yandex вернул статус %s", resp.status)
                    return []
                html_text = await resp.text()
    except Exception as e:
        logger.warning("Ошибка запроса к Yandex: %s", e)
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

    1. Ищет фото-кандидаты через Яндекс.Картинки
    2. Ранжирует их через CLIP ViT-B/32
    3. Возвращает лучшее изображение со статусом

    Возвращает словарь:
    {
        "best_url":        str | None,   # URL лучшего изображения
        "best_score":      float,        # итоговый ранговый балл R(I*)
        "status":          str,          # "accepted" / "needs_verification" / "no_match"
        "all_candidates":  list[dict],   # все ранжированные кандидаты
        "urls":            list[str],    # обратная совместимость — список URL
        "query_used":      str,
        "source":          str
    }
    """
    logger.info("Ищу фото: %s", product_name)

    # Шаг 1: поиск кандидатов через Яндекс (берём больше для отбора)
    search_count = max_results * 3
    urls = await search_yandex_images(product_name, max_results=search_count)

    empty_result = {
        "best_url": None,
        "best_score": 0,
        "status": "no_match",
        "all_candidates": [],
        "urls": [],
        "query_used": product_name,
        "source": "yandex.ru/images + CLIP ViT-B/32",
    }

    if not urls:
        return empty_result

    # Шаг 2: ранжирование через CLIP
    try:
        ranker = get_clip_ranker()
        ranked = await ranker.rank_images(product_name, urls)
    except Exception as exc:
        logger.error("Ошибка CLIP-ранжирования: %s", exc)
        # Fallback: возвращаем URL без ранжирования (как раньше)
        return {
            "best_url": urls[0] if urls else None,
            "best_score": 0,
            "status": "no_match",
            "all_candidates": [],
            "urls": urls[:max_results],
            "query_used": product_name,
            "source": "yandex.ru/images (CLIP недоступен)",
        }

    if not ranked:
        return empty_result

    # Шаг 3: выбор лучшего — формула (20)
    best = ranked[0]
    best_url = best["url"] if best["rank_score"] >= R_THRESHOLD else None

    return {
        "best_url": best_url,
        "best_score": best["rank_score"],
        "status": best["status"],
        "all_candidates": ranked[:max_results],
        "urls": [r["url"] for r in ranked[:max_results]],
        "query_used": product_name,
        "source": "yandex.ru/images + CLIP ViT-B/32",
    }
