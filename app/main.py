from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database.redis import connect_redis , close_redis




@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_redis()
    print("FastAPI started!")

    yield

    await close_redis()
    print("FastAPI stopped!")





app = FastAPI(lifespan=lifespan)
@app.get("/")
async def home():
    return {"message": "FastAPI is running"}





