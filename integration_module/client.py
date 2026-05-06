import aiohttp
from config import INTEGRATION_URL, ADAPTER_URL

async def get_products() -> list:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{INTEGRATION_URL}/products") as resp:
            if resp.status == 200:
                return await resp.json()
            return []

async def get_product(product_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{INTEGRATION_URL}/products/{product_id}") as resp:
            if resp.status == 200:
                return await resp.json()
            return {}

async def force_sync() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{ADAPTER_URL}/api/v1/sync/force") as resp:
            if resp.status == 200:
                return await resp.json()
            return {"status": "error"}

async def get_analytics() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{INTEGRATION_URL}/analytics/stats") as resp:
            if resp.status == 200:
                return await resp.json()
            return {}