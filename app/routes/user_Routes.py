import logging

from fastapi import APIRouter, HTTPException, status
from app.schema.user_Schema import SignupRequest, UserResponse
from app.models.user_Model import UserModel
from app.database.mongo import users_collection
from app.utils.password import hash_password


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)
# sign up routes 
@router.post('/register',response_model=UserResponse,status_code=status.HTTP_201_CREATED)
async def register_user(payload: SignupRequest):
    email = str(payload.email).lower()
    isExist = await users_collection.find_one({'email': email})
    if isExist:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail='User already Exist')
    user = UserModel(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password.get_secret_value()),
    )
    userdata=user.model_dump()
    try:
        result = await users_collection.insert_one(userdata)
    except Exception as e:
        logging.error(f"Database insertion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user in database"
        )
    return UserResponse(
        id=str(result.inserted_id),
          name=user.name,
        email=user.email,
        is_verified=user.is_verified
      
    )


    






