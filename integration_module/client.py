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

async def publish_to_avito(product_ids: list = None) -> dict:
    async with aiohttp.ClientSession() as session:
        payload = {"product_ids": product_ids} if product_ids else {}
        async with session.post(f"{INTEGRATION_URL}/avito/publish", json=payload) as resp:
            if resp.status == 200:
                return await resp.json()
            return {"status": "error"}


async def get_avito_products() -> list:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{INTEGRATION_URL}/avito/products") as resp:
            if resp.status == 200:
                return await resp.json()
            return []


async def get_analytics() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{INTEGRATION_URL}/analytics/stats") as resp:
            if resp.status == 200:
                return await resp.json()
            return {}
