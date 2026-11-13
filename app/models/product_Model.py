from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class ProductModel(BaseModel):

    user_id: str

    image_url: Optional[str] = None

    name: str
    category: str

    sku: str
    barcode: str

    buying_price: float
    selling_price: float

    unit: str

    current_stock: float
    low_stock_alert: float

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
