import logging
from datetime import datetime, timezone, timedelta
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

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# sign up routes
@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(payload: SignupRequest):
    email = str(payload.email).lower()
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
    email = str(payload.email).lower()
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not confirm_Password(
        plain_password=payload.password, hash_password=user["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    try:
        new_session = sessionModel(
            user_id=str(user["_id"]),
            ip=client_ip,
            user_agent=user_agent,
            refresh_token_hash=None,
            revoked_at=None,
            is_revoked=False,
        )
        session_result = await session_collection.insert_one(new_session.model_dump())
        session_id = str(session_result.inserted_id)
        access_token = createAccessToken(
            user_id=str(user["_id"]), session_id=session_id
        )
        refresh_token = createRefreshToken(
            user_id=str(user["_id"]), session_id=session_id
        )
        await session_collection.update_one(
            {"_id": session_result.inserted_id},
            {"$set": {"refresh_token_hash": refreshTokenHash(refresh_token)}},
        )
        # creating token object
        token_obj = TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )
        response_data = UserSigninResponse(
            id=str(user["_id"]), email=user["email"], token=token_obj
        )
    except Exception as e:
        logging.error(f"Sign in error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user from database",
        )
    return response_data
