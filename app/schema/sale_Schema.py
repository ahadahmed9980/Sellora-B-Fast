
from enum import Enum
from pydantic import ConfigDict


from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError , field_validator
from pydantic import BaseModel, ConfigDict, Field
from typing import Self

from fastapi import Form
from pydantic import BaseModel, ConfigDict, Field

class SaleItemSchema(BaseException):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku:str = Field(min_length=1, max_length=50)
    quantity: float = Field(gt=0)
    @field_validator("sku")
    @classmethod
    def lowercase_sku(cls, value: str) -> str:
        return value.lower()
class PaymentMethod(str, Enum):
    CASH = "cash"
    CREDIT = "credit"
class CustomerSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip().capitalize()
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("Phone number must contain only digits")
        if len(value) < 10 or len(value) > 15:
            raise ValueError("Phone number must be between 10 and 15 digits")
        return value

class CreateSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


    items: list[SaleItemSchema]
    payment_method: PaymentMethod
    customer: CustomerSchema | None = None
    amount_paid: float = Field(gt=0)
