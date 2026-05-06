import asyncio
import aiohttp
from config import VK_TOKEN, VK_GROUP_ID

async def main():
    async with aiohttp.ClientSession() as session:
        # 1. Тест: токен вообще работает?
        params = {"access_token": VK_TOKEN, "v": "5.131"}
        async with session.post("https://api.vk.com/method/groups.getById",
                                params={**params, "group_id": VK_GROUP_ID}) as r:
            print("groups.getById:", await r.json())

        # 2. Тест: список товаров (читать market)
        async with session.post("https://api.vk.com/method/market.get",
                                params={**params, "owner_id": f"-{VK_GROUP_ID}"}) as r:
            print("market.get:", await r.json())

        # 3. Тест: тот метод что падает
        async with session.post(
            "https://api.vk.com/method/photos.getMarketAlbumUploadServer",
            params={**params, "group_id": VK_GROUP_ID}) as r:
            print("photos.getMarketAlbumUploadServer:", await r.json())

asyncio.run(main())