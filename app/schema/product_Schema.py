
from enum import Enum
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError , field_validator
from pydantic import BaseModel, ConfigDict, Field
from typing import Self

from fastapi import Form
from pydantic import BaseModel, ConfigDict, Field



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
class CreateProductSchema(BaseModel):

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)
    category: ProductCategory
    sku: str = Field(min_length=1, max_length=50)
    barcode: str = Field(min_length=1, max_length=100)

    buying_price: float = Field(gt=0)
    selling_price: float = Field(gt=0)

    unit: UnitOfMeasurement
    current_stock: float = Field(ge=0)
    low_stock_alert: float = Field(ge=0)

    @field_validator("sku")
    @classmethod
    def lowercase_sku(cls, value: str) -> str:
        return value.lower()



    @classmethod
    def as_form(
    cls,
    name: str = Form(...),
    category: ProductCategory = Form(...),
    sku: str = Form(...),
    barcode: str = Form(...),
    buying_price: float = Form(...),
    selling_price: float = Form(...),
    unit: UnitOfMeasurement = Form(...),
    current_stock: float = Form(...),
    low_stock_alert: float = Form(...),
) -> Self:
        try:
            return cls(
                name=name,
                category=category,
                sku=sku,
                barcode=barcode,
                buying_price=buying_price,
                selling_price=selling_price,
                unit=unit,
                current_stock=current_stock,
                low_stock_alert=low_stock_alert,
            )
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc

