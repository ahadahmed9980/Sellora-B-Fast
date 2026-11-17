import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Request,
    Response,
    Cookie,
    Body,
    Header,
)
from app.schema.user_Schema import (
    SignupRequest,
    UserResponse,
    UserSigninResponse,
    SigninRequest,
    TokenResponse,
    RefreshRequest,
    RefreshResponse,
)
import jwt
from app.config import JWT_SECRET, JWT_ALGORITHM
from app.models.user_Model import UserModel
from app.models.session_Model import sessionModel
from app.database.mongo import users_collection, session_collection
from app.utils.password import hash_password, confirm_Password
from app.utils.tokens import createAccessToken, createRefreshToken, refreshTokenHash
from app.database.redis import redis_client

REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60  # 7 Days

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# sign up routes
@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(payload: SignupRequest):
    email = str(payload.email).lower().strip()
    isExist = await users_collection.find_one({"email": email})
    if isExist:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already Exist"
        )
    user = UserModel(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password.get_secret_value()),
    )
    userdata = user.model_dump()
    try:
        result = await users_collection.insert_one(userdata)
    except Exception as e:
        logging.error(f"Database insertion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user in database",
        )
    return UserResponse(
        id=str(result.inserted_id),
        name=user.name,
        email=user.email,
        is_verified=user.is_verified,
    )


# login user routes
@router.post("/login", response_model=UserSigninResponse, status_code=200)
async def login_user(payload: SigninRequest, request: Request, response: Response):
    email = str(payload.email).lower().strip()
    user = await users_collection.find_one({"email": email})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    if not confirm_Password(
        plain_password=payload.password, hash_password=user.get("password_hash")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    expire_time = datetime.now(timezone.utc) + timedelta(days=7)

    try:
        new_session_id = ObjectId()
        session_id_str = str(new_session_id)

        # 2. Tokens generate
        access_token = createAccessToken(
            user_id=str(user["_id"]), session_id=session_id_str
        )
        refresh_token = createRefreshToken(
            user_id=str(user["_id"]), session_id=session_id_str
        )

        new_session = sessionModel(
            user_id=str(user["_id"]),
            ip=client_ip,
            user_agent=user_agent,
            refresh_token_hash=refreshTokenHash(refresh_token),
            expires_at=expire_time,
            revoked_at=None,
            is_revoked="0",
        )

        session_doc = new_session.model_dump()
        session_doc["_id"] = new_session_id
        await session_collection.insert_one(session_doc)
        # now save session in redis
        redis_session_key = f"session:{session_id_str}"
        redis_session_data = {
            "userId": str(user["_id"]),
            "refreshTokenHash": refreshTokenHash(refresh_token),
            "is_revoked": "0",
            "name": user["name"],
            "email": user["email"],
        }
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.hset(redis_session_key, mapping=redis_session_data)
            pipe.expire(redis_session_key, REFRESH_TOKEN_EXPIRE_SECONDS)
            await pipe.execute()

        token_obj = TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

        response.set_cookie(
            key="refreshToken",
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_SECONDS,
            path="/",
        )

        return UserSigninResponse(
            id=str(user["_id"]), email=user["email"], token=token_obj
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Sign in error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process sign in request",
        )



@router.post("/rotate", response_model=RefreshResponse, status_code=200)
async def rotate(
    response: Response,
    data: RefreshRequest | None = Body(default=None),
    refresh_cookie: str | None = Cookie(default=None, alias="refreshToken"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):

    # 1. Get incoming refresh token

    incoming_token = (
        (data.refresh_token if data else None)
        or (
            authorization[7:].strip()
            if authorization and authorization.lower().startswith("bearer ")
            else None
        )
        or refresh_cookie
    )

    if not incoming_token:
        raise HTTPException(status_code=401, detail="Refresh Token required")

    # 2. Verify refresh token

    try:
        decoded = jwt.decode(
            incoming_token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        if decoded.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = ObjectId(decoded["id"])
        session_id = ObjectId(decoded["sessionId"])

    except HTTPException:
        raise

    except (jwt.InvalidTokenError, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    try:

        now = datetime.now(timezone.utc)

        incoming_hash = refreshTokenHash(incoming_token)

        redis_session_key = f"session:{session_id}"

        # 3. Check Redis session

        redis_session = await redis_client.hgetall(redis_session_key)

        if redis_session:

            print("REDIS SESSION FOUND:", redis_session)

            # Get user information from Redis

            user = {
                "name": redis_session["name"],
                "email": redis_session["email"]
            }

            if redis_session.get("userId") != str(user_id):
                raise HTTPException(401, "Invalid session")

            if redis_session.get("is_revoked") != "0":
                raise HTTPException(401, "Session revoked")

            if redis_session.get("refreshTokenHash") != incoming_hash:
                raise HTTPException(401, "Invalid refresh token")

        else:

            # 4. Redis MISS: Check MongoDB

            print("REDIS SESSION MISS: Checking MongoDB")

            user = await users_collection.find_one({
                "_id": user_id
            })

            session = await session_collection.find_one({
                "_id": session_id
            })

            if not user or not session:
                raise HTTPException(401, "Invalid session or user")

            if session.get("is_revoked") is True:
                raise HTTPException(401, "Session revoked")

            if session["expires_at"] <= now:
                raise HTTPException(401, "Session expired")

            if session.get("refresh_token_hash") != incoming_hash:
                raise HTTPException(401, "Invalid refresh token")

        # 5. Generate new tokens

        new_access_token = createAccessToken(
            user_id=str(user_id),
            session_id=str(session_id)
        )

        new_refresh_token = createRefreshToken(
            user_id=str(user_id),
            session_id=str(session_id)
        )

        new_refresh_hash = refreshTokenHash(new_refresh_token)

        # 6. Update MongoDB session

        update_result = await session_collection.update_one(
            {
                "_id": session_id,
                "user_id": str(user_id),
                "refresh_token_hash": incoming_hash,
                "is_revoked": False,
                "expires_at": {"$gt": now}
            },
            {
                "$set": {
                    "refresh_token_hash": new_refresh_hash,
                    "expires_at": now + timedelta(days=7)
                }
            }
        )

        print("MATCHED:", update_result.matched_count)

        if update_result.matched_count != 1:

            raise HTTPException(
                status_code=401,
                detail="Refresh token already used or session invalid"
            )

        # 7. Update Redis session

        async with redis_client.pipeline(transaction=True) as pipe:

            pipe.hset(
                redis_session_key,
                mapping={
                    "userId": str(user_id),
                    "refreshTokenHash": new_refresh_hash,
                    "is_revoked": "0",
                    "name": user["name"],
                    "email": user["email"]
                }
            )

            pipe.expire(
                redis_session_key,
                REFRESH_TOKEN_EXPIRE_SECONDS
            )

            await pipe.execute()

        # 8. Set refresh token cookie

        response.set_cookie(
            key="refreshToken",
            value=new_refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_SECONDS,
            path="/"
        )

        # 9. Return response

        return RefreshResponse(
            message="Token refreshed successfully",
            accessToken=new_access_token,
            refreshToken=new_refresh_token
        )

    except HTTPException:
        raise

    except Exception as e:

        logging.exception(f"Rotate error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Failed to process rotate request"
        )
