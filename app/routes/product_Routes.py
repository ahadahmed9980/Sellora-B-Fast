import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    status
)
from pymongo.errors import DuplicateKeyError
from app.schema.product_Schema import CreateProductSchema
from app.models