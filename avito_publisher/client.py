"""
Клиент API Авито для работы с сервисом Автозагрузка.

Основные операции:
    - Управление профилем автозагрузки (создание, чтение, обновление)
    - Запуск выгрузки объявлений из XML-файла по ссылке
    - Получение дерева категорий
    - Получение отчётов автозагрузки

Swagger-документация:
    https://developers.avito.ru/api-catalog/autoload/documentation
"""

import aiohttp
from avito_publisher.auth import get_auth_header

API_BASE = "https://api.avito.ru"


async def _request(method: str, path: str, **kwargs) -> dict:
    """Выполняет авторизованный запрос к API Авито."""
    headers = await get_auth_header()
    headers.update(kwargs.pop("headers", {}))

    async with aiohttp.ClientSession() as session:
        async with session.request(
            method, f"{API_BASE}{path}", headers=headers, **kwargs
        ) as resp:
            resp.raise_for_status()
            if resp.content_length == 0:
                return {}
            return await resp.json()


# ───────────────── Профиль автозагрузки ─────────────────


async def get_autoload_profile() -> dict:
    """Получить текущие настройки профиля автозагрузки.

    GET /autoload/v2/profile

    Возвращает:
        autoload_enabled, feeds_data, report_email, schedule и др.
    """
    return await _request("GET", "/autoload/v2/profile")


async def setup_autoload_profile(
    feed_url: str,
    feed_name: str = "Автозагрузка",
    report_email: str = "",
    schedule: list[dict] | None = None,
) -> dict:
    """Создать или обновить профиль автозагрузки.

    POST /autoload/v2/profile

    Args:
        feed_url: публичная HTTPS-ссылка на XML-файл с объявлениями
        feed_name: название фида (отображается в отчёте)
        report_email: email для получения отчётов
        schedule: расписание выгрузок, список словарей вида:
            [{"rate": 50, "weekdays": [0,1,2,3,4,5,6], "time_slots": [10]}]
            rate — кол-во объявлений за период
            weekdays — дни недели (0=пн, 6=вс)
            time_slots — часы (0-23, время МСК)

    Если schedule не указан, устанавливается расписание по умолчанию:
    каждый день в 10:00 МСК, до 100 объявлений.
    """
    if schedule is None:
        schedule = [
            {
                "rate": 100,
                "weekdays": [0, 1, 2, 3, 4, 5, 6],
                "time_slots": [10],
            }
        ]

    body = {
        "agreement": True,
        "autoload_enabled": True,
        "feeds_data": [
            {
                "feed_name": feed_name,
                "feed_url": feed_url,
            }
        ],
        "report_email": report_email,
        "schedule": schedule,
    }

    return await _request("POST", "/autoload/v2/profile", json=body)


# ───────────────── Запуск выгрузки ─────────────────


async def trigger_upload() -> dict:
    """Запустить выгрузку объявлений из файла по ссылке.

    POST /autoload/v1/upload

    Ограничение: не чаще 1 раза в час.
    Использует URL, указанный в профиле автозагрузки.
    """
    return await _request("POST", "/autoload/v1/upload")


# ───────────────── Категории ─────────────────


async def get_categories() -> dict:
    """Получить дерево категорий Авито.

    GET /autoload/v1/user-docs/tree

    Возвращает дерево вида:
        {"categories": [{"name": "...", "slug": "...", "nested": [...]}]}
    """
    return await _request("GET", "/autoload/v1/user-docs/tree")


async def get_category_fields(category_slug: str) -> dict:
    """Получить обязательные и опциональные поля категории.

    GET /autoload/v1/user-docs/node/{slug}/fields

    Args:
        category_slug: slug категории из дерева (например "telefony")

    Возвращает:
        {"node": {"name": "...", "slug": "..."}, "fields": [...]}
    """
    return await _request(
        "GET", f"/autoload/v1/user-docs/node/{category_slug}/fields"
    )


# ───────────────── Отчёты ─────────────────


async def get_reports(page: int = 1, per_page: int = 10) -> dict:
    """Получить список отчётов автозагрузки.

    GET /autoload/v2/reports
    """
    params = {"page": page, "per_page": per_page}
    return await _request("GET", "/autoload/v2/reports", params=params)


async def get_last_report() -> dict:
    """Получить последний завершённый отчёт.

    GET /autoload/v3/reports/last_completed_report
    """
    return await _request(
        "GET", "/autoload/v3/reports/last_completed_report"
    )


async def get_report(report_id: int) -> dict:
    """Получить конкретный отчёт по ID.

    GET /autoload/v3/reports/{report_id}
    """
    return await _request("GET", f"/autoload/v3/reports/{report_id}")


async def get_report_items(
    report_id: int, page: int = 1, per_page: int = 50
) -> dict:
    """Получить список объявлений из конкретного отчёта.

    GET /autoload/v2/reports/{report_id}/items
    """
    params = {"page": page, "per_page": per_page}
    return await _request(
        "GET", f"/autoload/v2/reports/{report_id}/items", params=params
    )


async def get_report_items_by_ids(ad_ids: str) -> dict:
    """Получить данные по конкретным объявлениям в автозагрузке.

    GET /autoload/v2/reports/items

    Args:
        ad_ids: строка с ID объявлений через запятую (до 100 шт.)
                Это ID из XML-фида (тег <Id>), не Avito ID.
    """
    params = {"query": ad_ids}
    return await _request("GET", "/autoload/v2/reports/items", params=params)


async def get_report_fees(report_id: int, page: int = 1, per_page: int = 50) -> dict:
    """Получить списания за объявления в конкретной выгрузке.

    GET /autoload/v2/reports/{report_id}/items/fees
    """
    params = {"page": page, "per_page": per_page}
    return await _request(
        "GET", f"/autoload/v2/reports/{report_id}/items/fees", params=params
    )
