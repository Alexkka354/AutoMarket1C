import aiohttp
from config import VK_TOKEN, VK_GROUP_ID

VK_API = "https://api.vk.com/method"
VERSION = "5.131"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def get_upload_server() -> str:
    async with aiohttp.ClientSession() as session:
        params = {
            "group_id": VK_GROUP_ID,
            "access_token": VK_TOKEN,
            "v": VERSION,
        }
        async with session.post(
            f"{VK_API}/photos.getMarketAlbumUploadServer", params=params
        ) as resp:
            data = await resp.json()
            print(f"Upload server response: {data}")
            return data["response"]["upload_url"]


async def _download_image(photo_url: str) -> bytes:
    """Скачиваем фото с браузерным User-Agent чтобы не получать 403."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(photo_url, headers=headers, timeout=30) as resp:
            resp.raise_for_status()
            return await resp.read()


async def upload_photo(photo) -> int:
    """Загружает фото в VK Market.
    Аргумент `photo` может быть:
      - строкой (URL) — фото будет скачано
      - bytes — уже скачанные данные изображения
    """
    if isinstance(photo, bytes):
        photo_data = photo
    else:
        photo_data = await _download_image(photo)
        print(f"Photo downloaded: {len(photo_data)} bytes")

    async with aiohttp.ClientSession() as session:
        upload_url = await get_upload_server()
        print(f"Upload URL: {upload_url}")

        form = aiohttp.FormData()
        form.add_field(
            "file", photo_data, filename="photo.jpg", content_type="image/jpeg"
        )
        async with session.post(upload_url, data=form) as resp:
            upload_result = await resp.json()
            print(f"Upload result: {upload_result}")

        params = {
            "group_id": VK_GROUP_ID,
            "photo": upload_result["photo"],
            "server": upload_result["server"],
            "hash": upload_result["hash"],
            "access_token": VK_TOKEN,
            "v": VERSION,
        }
        async with session.post(
            f"{VK_API}/photos.saveMarketAlbumPhoto", params=params
        ) as resp:
            save_result = await resp.json()
            print(f"Save result: {save_result}")
            return save_result["response"][0]["id"]


async def add_product(
    title: str,
    description: str,
    price: float,
    photo_url=None,
    category_id: int = 1,
) -> dict:
    """Создаёт товар в VK Market.
    `photo_url` может быть URL (str), bytes или None.
    """
    async with aiohttp.ClientSession() as session:
        main_photo_id = None

        if photo_url:
            try:
                main_photo_id = await upload_photo(photo_url)
                print(f"✅ Фото загружено, ID: {main_photo_id}")
            except Exception as e:
                import traceback
                print(f"❌ Ошибка загрузки фото: {e}")
                print(traceback.format_exc())

        params = {
            "owner_id": f"-{VK_GROUP_ID}",
            "name": title,
            "description": description,
            "category_id": category_id,
            "price": price,
            "access_token": VK_TOKEN,
            "v": VERSION,
        }
        if main_photo_id:
            params["main_photo_id"] = main_photo_id

        async with session.post(f"{VK_API}/market.add", params=params) as resp:
            return await resp.json()


async def edit_product(
    item_id: int, title: str, description: str, price: float
) -> dict:
    async with aiohttp.ClientSession() as session:
        params = {
            "owner_id": f"-{VK_GROUP_ID}",
            "item_id": item_id,
            "name": title,
            "description": description,
            "price": price,
            "access_token": VK_TOKEN,
            "v": VERSION,
        }
        async with session.post(f"{VK_API}/market.edit", params=params) as resp:
            return await resp.json()


async def get_products() -> dict:
    async with aiohttp.ClientSession() as session:
        params = {
            "owner_id": f"-{VK_GROUP_ID}",
            "access_token": VK_TOKEN,
            "v": VERSION,
            "count": 50,
        }
        async with session.post(f"{VK_API}/market.get", params=params) as resp:
            return await resp.json()


async def delete_product(item_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        params = {
            "owner_id": f"-{VK_GROUP_ID}",
            "item_id": item_id,
            "access_token": VK_TOKEN,
            "v": VERSION,
        }
        async with session.post(f"{VK_API}/market.delete", params=params) as resp:
            return await resp.json()
