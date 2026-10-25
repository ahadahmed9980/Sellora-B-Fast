from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database.redis import connect_redis, close_redis
from app.database.mongo import create_indexes
from app.routes.user_Routes import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_redis()
    print("FastAPI started!")
    await create_indexes()

    yield

    await close_redis()
    print("FastAPI stopped!")


app = FastAPI(lifespan=lifespan)
app.include_router(user_router)


@app.get("/")
async def home():
    return {"message": "FastAPI is running"}
