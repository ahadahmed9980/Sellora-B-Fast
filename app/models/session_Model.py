from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class sessionModel(BaseException):
    user_id: str
    refresh_token_hash: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
