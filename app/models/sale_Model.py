from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime, timezone



class SaleItemModel(BaseModel):
    product_id: str
    sku: str
    name: str
    quantity: float
    unit: str
    unit_price: float
    subtotal: float

class CustomerModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str
    phone: str
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("Phone number must contain only digits")
        if len(value) < 10 or len(value) > 15:
            raise ValueError("Phone number must be between 10 and 15 digits")
        return value

class SaleModel(BaseModel):
    user_id: str
    invoice_number: str

    items: list[SaleItemModel]

    total_amount: float
    amount_paid: float
    remaining_amount: float

    payment_method: str
    payment_status: str

    customer: Optional[CustomerModel] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
