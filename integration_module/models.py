from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductSync(BaseModel):
    name: str
    article: str
    stock: int
    price: float
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    article: str
    category: Optional[str]
    price: float
    stock: int
    description: Optional[str]
    image_url: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime