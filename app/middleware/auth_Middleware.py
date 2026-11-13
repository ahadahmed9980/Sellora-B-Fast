from fastapi import HTTPException, Request, status
from bson import ObjectId
from bson.errors import InvalidId

import jwt
from jwt.exceptions import InvalidTokenError

from app.config import JWT_SECRET, JWT_ALGORITHM
from app.database.mongo import users_collection, session_collection
from app.database.redis import redis_client


async def get_current_user(request: Request):

    # 1. Get access token
    authorization = request.headers.get("Authorization", "")

    token = None

    if authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]

    token = token or request.cookies.get("accessToken") or request.cookies.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is required"
        )

    # 2. Verify JWT
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        user_id = ObjectId(decoded["id"])
        session_id = ObjectId(decoded["sessionId"])

    except (InvalidTokenError, InvalidId, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    # 3. Redis session lookup
    session_key = f"session:{session_id}"

    redis_session = await redis_client.hgetall(session_key)

    # 4. Redis HIT
    if redis_session:

        # Verify user ID
        if redis_session.get("userId") != str(user_id):
            raise HTTPException(status_code=401, detail="Invalid session")

        # Verify session revocation
        if redis_session.get("is_revoked") != "0":
            raise HTTPException(status_code=401, detail="Session has been revoked")

        # Verify user status

        # Build user data from Redis
        user = {
            "_id": user_id,
            "name": redis_session.get("name"),
            "email": redis_session.get("email"),
        }

        request.state.session_id = session_id
        request.state.user = user

        return user

    # 5. Redis MISS -> MongoDB fallback
    else:
        session = await session_collection.find_one(
            {"_id": session_id, "userId": user_id, "is_revoked": 0}
        )

    if not session:
        raise HTTPException(status_code=401, detail="Session is invalid or revoked")

    # 6. Verify user in MongoDB
    user = await users_collection.find_one({"_id": user_id, "status": "active"})

    if not user:
        raise HTTPException(
            status_code=403, detail="User not found or account inactive"
        )

    # 7. Populate Redis cache
    redis_session_data = {
        "userId": str(user_id),
        "refreshTokenHash": session.get("refreshTokenHash", ""),
        "is_revoked": "0",
        "name": user.get("name", ""),
        "email": user.get("email", ""),
    }

    await redis_client.hset(session_key, mapping=redis_session_data)

    await redis_client.expire(session_key, 600)

    # 8. Request state
    request.state.session_id = session_id
    request.state.user = user

    return user
