from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from integration_module.models import ProductSync
from integration_module import database
from contextlib import asynccontextmanager
from pydantic import BaseModel


class ProductUpdate(BaseModel):
    description: Optional[str] = None
    image_url:   Optional[str] = None
    category:    Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.create_products_table()
    print("✅ Таблица products создана!")
    yield

app = FastAPI(title="AutoMarket Integration Module", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PublishRequest(BaseModel):
    product_ids: Optional[List[int]] = None


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


@app.patch("/products/{product_id}")
async def patch_product(product_id: int, update: ProductUpdate):
    try:
        await database.update_product(
            product_id,
            description=update.description,
            image_url=update.image_url,
            category=update.category
        )
        return {"status": "ok", "updated": product_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/avito/publish")
async def avito_publish(request: PublishRequest = None):
    try:
        ids = request.product_ids if request else None
        count = await database.publish_to_avito(ids)
        return {
            "status": "ok",
            "published": count,
            "message": f"Опубликовано {count} товаров на Авито"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/avito/unpublish")
async def avito_unpublish(request: PublishRequest = None):
    try:
        ids = request.product_ids if request else None
        count = await database.unpublish_from_avito(ids)
        return {
            "status": "ok",
            "unpublished": count,
            "message": f"Снято с публикации {count} товаров"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/avito/products")
async def avito_products():
    try:
        products = await database.get_avito_products()
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
