import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Request
from app.schema.user_Schema import (
    SignupRequest,
    UserResponse,
    UserSigninResponse,
    SigninRequest,
    TokenResponse,
)
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
async def login_user(payload: SigninRequest, request: Request):
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
            is_revoked=False,
        )

        session_doc = new_session.model_dump()
        session_doc["_id"] = new_session_id
        await session_collection.insert_one(session_doc)
        # now save session in redis 
        redis_session_key = f'session:{session_id_str}'
        redis_session_data = {
            "userId": str(user["_id"]),
            "refreshTokenHash": refreshTokenHash,
            "is_revoked": "0",
        }
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.hset(redis_session_key, mapping=redis_session_data)
            pipe.expire(redis_session_key, REFRESH_TOKEN_EXPIRE_SECONDS)
            await pipe.execute()

        token_obj = TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
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
