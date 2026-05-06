import asyncio
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from scheduler import sync_loop
from client import OneCClient
from publisher import IntegrationPublisher

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск фонового планировщика при старте
    task = asyncio.create_task(sync_loop())
    yield
    task.cancel()

app = FastAPI(title="1C Adapter", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

# Эндпоинт для принудительной синхронизации (вызывается из Telegram-бота)
@app.post("/api/v1/sync")
async def force_sync():
    client = OneCClient()
    publisher = IntegrationPublisher()
    products = await client.fetch_products()
    await publisher.send_products(products)
    return {"synced": len(products)}

# Событийный webhook — 1С вызывает при изменении цены/остатка
@app.post("/api/v1/webhook/product-updated")
async def product_updated(product_id: str):
    client = OneCClient()
    publisher = IntegrationPublisher()
    product = await client.fetch_product(product_id)
    await publisher.send_update(product)
    return {"updated": product_id}