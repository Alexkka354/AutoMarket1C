import asyncpg
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "automarket")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")

async def get_connection():
    return await asyncpg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

async def create_products_table():
    conn = await get_connection()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(500),
            article     VARCHAR(100) UNIQUE,
            category    VARCHAR(200),
            price       DECIMAL(10,2),
            stock       INTEGER,
            description TEXT,
            image_url   VARCHAR(500),
            status      VARCHAR(50) DEFAULT 'active',
            published_avito BOOLEAN DEFAULT FALSE,
            created_at  TIMESTAMP DEFAULT NOW(),
            updated_at  TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'published_avito'
            ) THEN
                ALTER TABLE products ADD COLUMN published_avito BOOLEAN DEFAULT FALSE;
            END IF;
        END $$;
    """)
    await conn.close()

async def upsert_products(products: list) -> int:
    conn = await get_connection()
    count = 0
    for p in products:
        status = 'active' if p.get('stock', 0) > 0 else 'inactive'
        await conn.execute("""
            INSERT INTO products (name, article, stock, price, category, description, image_url, status, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            ON CONFLICT (article) DO UPDATE SET
                name = EXCLUDED.name,
                price = EXCLUDED.price,
                stock = EXCLUDED.stock,
                status = EXCLUDED.status,
                updated_at = NOW()
        """, p['name'], p['article'], p['stock'], p['price'],
            p.get('category'), p.get('description'), p.get('image_url'), status)
        count += 1
    await conn.close()
    return count

async def get_all_products() -> list:
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT * FROM products WHERE status = 'active' ORDER BY updated_at DESC
    """)
    await conn.close()
    return [dict(row) for row in rows]

async def get_product_by_id(product_id: int) -> Optional[dict]:
    conn = await get_connection()
    row = await conn.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
    await conn.close()
    return dict(row) if row else None

async def publish_to_avito(product_ids: list = None) -> int:
    conn = await get_connection()
    if product_ids:
        count = await conn.fetchval("""
            UPDATE products SET published_avito = TRUE, updated_at = NOW()
            WHERE id = ANY($1::int[]) AND status = 'active'
            RETURNING COUNT(*)
        """, product_ids)
    else:
        count = await conn.fetchval("""
            WITH updated AS (
                UPDATE products SET published_avito = TRUE, updated_at = NOW()
                WHERE status = 'active' AND published_avito = FALSE
                RETURNING 1
            ) SELECT COUNT(*) FROM updated
        """)
    await conn.close()
    return count or 0


async def unpublish_from_avito(product_ids: list = None) -> int:
    conn = await get_connection()
    if product_ids:
        count = await conn.fetchval("""
            WITH updated AS (
                UPDATE products SET published_avito = FALSE, updated_at = NOW()
                WHERE id = ANY($1::int[])
                RETURNING 1
            ) SELECT COUNT(*) FROM updated
        """, product_ids)
    else:
        count = await conn.fetchval("""
            WITH updated AS (
                UPDATE products SET published_avito = FALSE, updated_at = NOW()
                WHERE published_avito = TRUE
                RETURNING 1
            ) SELECT COUNT(*) FROM updated
        """)
    await conn.close()
    return count or 0


async def get_avito_products() -> list:
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT * FROM products
        WHERE published_avito = TRUE AND status = 'active'
        ORDER BY updated_at DESC
    """)
    await conn.close()
    return [dict(row) for row in rows]


async def get_stats() -> dict:
    conn = await get_connection()
    total = await conn.fetchval("SELECT COUNT(*) FROM products")
    active = await conn.fetchval("SELECT COUNT(*) FROM products WHERE status = 'active'")
    last_sync = await conn.fetchval("SELECT MAX(updated_at) FROM products")
    await conn.close()
    return {
        "products_count": total,
        "active_products": active,
        "last_sync": str(last_sync) if last_sync else "нет данных",
        "views": 0,
        "clicks": 0,
        "responses": 0,
        "sales": 0
    }
