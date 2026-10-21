from pymongo import ASCENDING, AsyncMongoClient
from app.config import MONGO_URI, DB_NAME

client = AsyncMongoClient(MONGO_URI)
db = client[DB_NAME]
