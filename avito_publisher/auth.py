"""
Модуль авторизации в API Авито.
Реализует OAuth2 client_credentials flow.

Авторизация:
    1. Отправляем POST-запрос на https://api.avito.ru/token/
       с client_id и client_secret
    2. Получаем access_token (действует 24 часа)
    3. Кешируем токен, обновляем за 60 сек до истечения
"""

import time
import aiohttp
from avito_publisher.config import AVITO_CLIENT_ID, AVITO_CLIENT_SECRET

TOKEN_URL = "https://api.avito.ru/token/"

_token_cache: dict = {
    "access_token": None,
    "expires_at": 0.0,
}


async def get_access_token() -> str:
    """Получает access_token по OAuth2 client_credentials.

    Токен кешируется в памяти и обновляется автоматически
    за 60 секунд до истечения срока действия (24 часа).
    """
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    payload = {
        "grant_type": "client_credentials",
        "client_id": AVITO_CLIENT_ID,
        "client_secret": AVITO_CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with aiohttp.ClientSession() as session:
        async with session.post(TOKEN_URL, data=payload, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 86400) - 60

    return _token_cache["access_token"]


async def get_auth_header() -> dict:
    """Возвращает заголовок Authorization для запросов к API Авито."""
    token = await get_access_token()
    return {"Authorization": f"Bearer {token}"}
