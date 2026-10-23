from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserModel(BaseModel):
    name: str
    email: str
    password_hash: str
    role: str = "owner"
    is_verified: bool = False
    created_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc)
  )
    updated_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc)
  )
