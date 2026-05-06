import aiohttp
from avito.auth import get_auth_header

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
    """GET /autoload/v2/profile — настройки профиля автозагрузки."""
    return await _request("GET", "/autoload/v2/profile")


async def update_autoload_profile(
    feed_url: str,
    feed_name: str = "Автозагрузка",
    report_email: str = "",
    schedule: list[dict] | None = None,
) -> dict:
    """POST /autoload/v2/profile — создание / обновление профиля.

    feed_url — публичная ссылка на XML-файл с объявлениями.
    feed_name — название фида (отображается в отчёте).
    schedule — расписание выгрузок:
        [{"rate": 50, "weekdays": [0..6], "time_slots": [0..23]}]
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
    """POST /autoload/v1/upload — запуск выгрузки по ссылке из профиля.

    Ограничение: не чаще 1 раза в час.
    """
    return await _request("POST", "/autoload/v1/upload")


# ───────────────── Категории ─────────────────


async def get_categories_tree() -> dict:
    """GET /autoload/v1/user-docs/tree — дерево категорий Авито."""
    return await _request("GET", "/autoload/v1/user-docs/tree")


async def get_category_fields(node_slug: str) -> dict:
    """GET /autoload/v1/user-docs/node/{slug}/fields — поля категории."""
    return await _request(
        "GET", f"/autoload/v1/user-docs/node/{node_slug}/fields"
    )


# ───────────────── Отчёты ─────────────────


async def get_reports(page: int = 1, per_page: int = 10) -> dict:
    """GET /autoload/v2/reports — список отчётов автозагрузки."""
    params = {"page": page, "per_page": per_page}
    return await _request("GET", "/autoload/v2/reports", params=params)


async def get_last_report() -> dict:
    """GET /autoload/v3/reports/last_completed_report — последний отчёт."""
    return await _request(
        "GET", "/autoload/v3/reports/last_completed_report"
    )


async def get_report(report_id: int) -> dict:
    """GET /autoload/v3/reports/{report_id} — конкретный отчёт."""
    return await _request("GET", f"/autoload/v3/reports/{report_id}")


async def get_report_items(
    report_id: int, page: int = 1, per_page: int = 50
) -> dict:
    """GET /autoload/v2/reports/{report_id}/items — объявления из отчёта."""
    params = {"page": page, "per_page": per_page}
    return await _request(
        "GET", f"/autoload/v2/reports/{report_id}/items", params=params
    )


# ───────────────── ID-маппинг ─────────────────


async def get_avito_ids(ad_ids: list[str]) -> dict:
    """GET /autoload/v2/items/avito_ids — Avito ID по ID из файла."""
    params = {"query": ",".join(ad_ids)}
    return await _request("GET", "/autoload/v2/items/avito_ids", params=params)


async def get_ad_ids(avito_ids: list[int]) -> dict:
    """GET /autoload/v2/items/ad_ids — ID из файла по Avito ID."""
    params = {"query": ",".join(str(i) for i in avito_ids)}
    return await _request("GET", "/autoload/v2/items/ad_ids", params=params)
