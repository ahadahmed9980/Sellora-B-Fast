from pymongo import ASCENDING, AsyncMongoClient
from app.config import MONGO_URI, DB_NAME

client = AsyncMongoClient(MONGO_URI)
db = client[DB_NAME]

users_collection = db["users"]
session_collection = db["sessions"]


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
