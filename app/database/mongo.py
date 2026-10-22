from pymongo import ASCENDING, AsyncMongoClient
from app.config import MONGO_URI, DB_NAME

client = AsyncMongoClient(MONGO_URI)
db = client[DB_NAME]

users_collection = db["users"]


async def create_indexes():
    await users_collection.create_index([("email", ASCENDING)], unique=True)
