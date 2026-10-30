import asyncio
from fastapi import HTTPException, Request, status
from bson import ObjectId
from bson.errors import InvalidId
import jwt
from jwt.exceptions import InvalidTokenError

from app.config import JWT_SECRET, JWT_ALGORITHM
from app.database.mongo import users_collection, session_collection


async def get_current_user(request: Request):
    # 1. Fast Token Extraction
    auth = request.headers.get("Authorization")
    token = None
    if auth and auth.startswith("Bearer "):
        token = auth[7:]
    else:
        token = request.cookies.get("accessToken") or request.cookies.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is required"
        )

    # 2. JWT Decode
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = ObjectId(decoded["id"])
        session_id = ObjectId(decoded["sessionId"])
    except (InvalidTokenError, InvalidId, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    # 3. Parallel DB Queries + Projections (Half latency)
    user_query = users_collection.find_one(
        {"_id": user_id},
        projection={"password": 0, "passwordHash": 0}  
    )
    session_query = session_collection.find_one(
        {"_id": session_id, "userId": user_id, "revoke": False},
        projection={"_id": 1, "userId": 1, "revoke": 1} 
    )

    user, session = await asyncio.gather(user_query, session_query)

    # 4. Fast Validation Checks
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or revoked"
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    request.state.session = session
    return user