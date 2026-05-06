from fastapi import FastAPI, HTTPException
from typing import List
from integration_module.models import ProductSync
from integration_module import database
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.create_products_table()
    print("✅ Таблица products создана!")
    yield

app = FastAPI(title="AutoMarket Integration Module", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/v1/products/sync")
async def sync_products(products: List[ProductSync]):
    try:
        data = [p.model_dump() for p in products]
        count = await database.upsert_products(data)
        return {
            "status": "ok",
            "synced": count,
            "message": f"Успешно синхронизировано {count} товаров"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products")
async def get_products():
    try:
        products = await database.get_all_products()
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{product_id}")
async def get_product(product_id: int):
    product = await database.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

@app.post("/sync/start")
async def sync_start():
    return {"status": "ok", "message": "Выгрузка запущена"}

@app.post("/sync/stop")
async def sync_stop():
    return {"status": "ok", "message": "Выгрузка остановлена"}

@app.get("/analytics/stats")
async def analytics_stats():
    try:
        stats = await database.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))