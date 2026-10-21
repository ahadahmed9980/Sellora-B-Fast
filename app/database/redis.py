import redis.asyncio as redis
from app.config import REDIS_URL

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


async def connect_redis():
    await redis_client.ping()
    print("Redis connected successfully!")


async def close_redis():
    await redis_client.aclose()
    print("Redis connection closed!")
