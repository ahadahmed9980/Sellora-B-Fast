from pymongo import ASCENDING, AsyncMongoClient
from app.config import MONGO_URI, DB_NAME

client = AsyncMongoClient(MONGO_URI)
db = client[DB_NAME]

users_collection = db["users"]
session_collection = db["sessions"]
products_collection = db["products"]


async def create_indexes():
    await users_collection.create_index([("email", ASCENDING)], unique=True)
    await session_collection.create_index(
        [("revokedAt", ASCENDING)],
        expireAfterSeconds=0,
        partialFilterExpression={"isRevoked": True},
        name="auto_delete_revoked_sessions_ttl",
    )
    await session_collection.create_index(
        [("userId", ASCENDING), ("isRevoked", ASCENDING)],
        name="user_active_sessions_idx",
    )
    # Products index: barcode search
    await products_collection.create_index(
        [
            ("user_id", ASCENDING),
            ("basic_details.barcode", ASCENDING),
        ],
        unique=True,
        partialFilterExpression={"basic_details.barcode": {"$type": "string"}},
        name="unique_user_barcode_idx",
    )
