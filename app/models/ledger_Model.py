
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional


class LedgerModel(BaseModel):
    user_id: str
    sale_id: str
    invoice_number: str

    entry_type: str
    amount: float

    customer_name: str
    customer_mobile: Optional[str] = None

    description: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
