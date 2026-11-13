import re
from typing import Self
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


# fixed cate
class ProductCategory(str, Enum):
    GROCERY = "grocery"
    BAKERY = "bakery"
    PHARMACY = "pharmacy"


class UnitOfMeasurement(str, Enum):
    PIECE = "piece"
    KG = "kg"
    GRAM = "gram"
    LITER = "liter"
    ML = "ml"
    PACK = "pack"
    DOZEN = "dozen"


# create product
class CreateProductSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    # product image
    imageUrl: str | None = None
    name: str = Field(min_length=2, max_length=100)
    category: ProductCategory
    sku: str = Field(min_length=1, max_length=50)
    barcode: str = Field(min_length=1, max_length=100)
    bying_price: float = Field(gt=0)
    selling_price: float = Field(gt=0)
    unit: UnitOfMeasurement
    current_stock: float = Field(ge=0)
    low_stock_alert: float = Field(ge=0)
