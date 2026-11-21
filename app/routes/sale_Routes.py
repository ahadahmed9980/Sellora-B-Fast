import json
from unittest import result
import uuid

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import UpdateOne
from pymongo.errors import PyMongoError

from app.database.mongo import (client, sale_collection , ledger_collection , stock_movements_collection,products_collection)
from app.schema.sale_Schema import CreateSaleSchema
from app.middleware.auth_Middleware import get_current_user
from app.database.redis import redis_client
from app.models.sale_Model import (SaleModel, SaleItemModel , CustomerModel)
from app.models.ledger_Model import LedgerModel
from app.models.stock_movement_Model import StockMovementModel
router = APIRouter(
    prefix="/api/sales",
    tags=["Sales"]
)



router = APIRouter(prefix="/api/sales", tags=["Sales"])


@router.post("/create-sale", status_code=status.HTTP_201_CREATED)
async def create_sale(
    payload: CreateSaleSchema,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])

    # Credit sale requires customer details
    if payload.payment_method == "credit" and not payload.customer:
        raise HTTPException(
            status_code=400,
            detail="Customer details are required for credit sale"
        )

    # Combine duplicate SKUs
    cart = {}

    for item in payload.items:
        sku = item.sku.strip().lower()

        if sku in cart:
            cart[sku] += item.quantity
        else:
            cart[sku] = item.quantity

    mongo_items = []
    update_operations = []
    total_amount = 0

    async with  client.start_session() as session:
        try:
            async with await session.start_transaction():

                # Find and verify every product
                for sku, quantity in cart.items():

                    product = await products_collection.find_one(
                        {
                            "user_id": user_id,
                            "sku": sku
                        },
                        session=session
                    )

                    if not product:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Product not found: {sku}"
                        )

                    selling_price = product ["selling_price"]
                    product_name = product ["name"]
                    unit = product ["unit"]

                    subtotal = selling_price * quantity
                    total_amount += subtotal

                    mongo_items.append(
                        SaleItemModel(
                            product_id=str(product["_id"]),
                            sku=sku,
                            name=product_name,
                            quantity=quantity,
                            unit=unit,
                            unit_price=selling_price,
                            subtotal=subtotal
                        ).model_dump()
                    )

                    # Prepare stock update
                    update_operations.append(
                        UpdateOne(
                            {
                                "_id": product["_id"],
                                "user_id": user_id,
                                "inventory.current_stock": {
                                    "$gte": quantity
                                }
                            },
                            {
                                "$inc": {
                                    "inventory.current_stock": -quantity
                                }
                            }
                        )
                    )

                # Validate payment
                if payload.amount_paid > total_amount:
                    raise HTTPException(
                        status_code=400,
                        detail="Amount paid cannot exceed total amount"
                    )

                if (
                    payload.payment_method == "cash"
                    and payload.amount_paid != total_amount
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Cash payment must equal total amount"
                    )

                # Update all product stocks
                if update_operations:
                    result = await products_collection.bulk_write(
                        update_operations,
                        ordered=True,
                        session=session
                    )
                    print("Matched:", result.matched_count)
                    print("Modified:", result.modified_count)
                    print("Operations:", len(update_operations))

                    if result.modified_count != len(update_operations):
                        raise HTTPException(
                            status_code=400,
                            detail="Insufficient stock for one or more products"
                        )

                # Create invoice
                remaining_amount = total_amount - payload.amount_paid

                payment_status = (
                    "paid" if remaining_amount == 0
                    else "unpaid" if payload.amount_paid == 0
                    else "partial"
                )

                invoice_number = f"INV-{uuid.uuid4().hex[:10].upper()}"

                sale = SaleModel(
                    user_id=user_id,
                    invoice_number=invoice_number,
                    items=mongo_items,
                    total_amount=total_amount,
                    amount_paid=payload.amount_paid,
                    remaining_amount=remaining_amount,
                    payment_method=payload.payment_method.value,
                    payment_status=payment_status,
                    customer=payload.customer,
                    created_at=datetime.now(timezone.utc)
                )

                sale_document = sale.model_dump()

                insert_result = await sale_collection.insert_one(
                    sale_document,
                    session=session
                )

                sale_document["_id"] = str(insert_result.inserted_id)

            # Transaction committed successfully

        except HTTPException:
            raise

        except PyMongoError:
            raise HTTPException(
                status_code=500,
                detail="Sale transaction failed"
            )

    # Invalidate Redis cache after successful commit
    for sku in cart:
        try:
            await redis_client.delete(f"product:{user_id}:{sku}")
        except Exception:
            pass

    return {
        "success": True,
        "message": "Sale created successfully",
        "sale": sale_document
    }
