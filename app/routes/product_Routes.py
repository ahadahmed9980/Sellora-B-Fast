
import logging

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    status,
)

from pymongo.errors import DuplicateKeyError

from app.middleware.auth_Middleware import get_current_user
from app.database.mongo import products_collection

from app.schema.product_Schema import CreateProductSchema
from app.models.product_Model import ProductModel

from app.services.cloudinary_Services import upload_image


router = APIRouter(
    prefix="/api/products",
    tags=["Products"],
)


@router.post(
    "/create-product",
    status_code=status.HTTP_201_CREATED
)
async def create_product(

    payload: CreateProductSchema = Depends(
        CreateProductSchema.as_form
    ),

    image: UploadFile | None = File(None),

    current_user: dict = Depends(get_current_user)

):

    # 1. Get authenticated user ID

    user_id = str(current_user["_id"])


    # 2. Check duplicate SKU or Barcode

    is_exist = await products_collection.find_one({

        "user_id": user_id,

        "$or": [
            {"sku": payload.sku},
            {"barcode": payload.barcode}
        ]

    })

    if is_exist:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product SKU or Barcode already exists"
        )


    # 3. Upload image to Cloudinary

    image_url = None

    if image:

        uploaded_image = await upload_image(image)

        image_url = uploaded_image["image_url"]


    # 4. Create product model

    product = ProductModel(

        user_id=user_id,

        image_url=image_url,

        **payload.model_dump()

    )


    # 5. Save product in MongoDB

    try:

        result = await products_collection.insert_one(
            product.model_dump()
        )

    except DuplicateKeyError:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product SKU or Barcode already exists"
        )

    except Exception:

        logging.exception("Product creation failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
        )


    # 6. Return response

    return {

        "success": True,

        "message": "Product created successfully",

        "product_id": str(result.inserted_id)

    }

@router.get("/my-products", status_code=status.HTTP_200_OK)
async def get_products(page : int = 1 , limit : int = 10 ,
        current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    skip = (page - 1) * limit
    products = await products_collection.find({"user_id": user_id}).skip(skip).limit(limit).to_list(length=limit)
    total_products = await products_collection.count_documents({"user_id": user_id})
    for product in products:
        product['_id'] = str(product['_id'])
    return {
        "success": True,
        "total_products": total_products,
        "current_page": page,
        "limit": limit,
        "total_pages": (total_products + limit - 1) // limit,
        "products": products
    }