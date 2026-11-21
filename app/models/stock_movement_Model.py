
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class StockMovementModel(BaseModel):
    user_id: str
    sale_id: str

    product_id: str
    sku: str
    product_name: str

    movement_type: str = "OUT"
    reason: str = "SALE"

    quantity: float

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
