import re
from typing import Self, Optional
from datetime import datetime, timezone
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class SessionRequest(BaseModel):
    user_id: str = Field(..., alias="userId", description="user Id")
    ip: Optional[str] = Field(None, description="Client IP address")
    refresh_token_hash: Optional[str] = Field(
        None, alias="RefreshTokenHash", description="RefreshToken hash"
    )
    user_agent: Optional[str] = Field(None, alias="userAgent")
    is_revoked: bool = Field(default=False, alias="isRevoked")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAt",
    )
    expires_at: Optional[datetime] = Field(
        None,
        alias="expiresAt",
        description="Session expiry date",
    )
    model_config = ConfigDict(
        populate_by_name=True,
    )
