import re
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class SignupRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
    confirm_password: SecretStr = Field(min_length=8, max_length=128)
    role: str = Field(default="user")
    accept_terms: bool
    is_verified: bool = Field(default=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password", "confirm_password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        raw_password = value.get_secret_value()

        pattern = (
            r"^(?=.*[A-Za-z])" r"(?=.*\d)" r"(?=.*[@$!%*?&])" r"[A-Za-z\d@$!%*?&]{8,}$"
        )

        if not re.match(pattern, raw_password):
            raise ValueError(
                "Password must be at least 8 characters and contain letters, "
                "numbers, and a special character"
            )

        if len(raw_password.encode("utf-8")) > 72:
            raise ValueError("Password exceeds the supported byte length")

        return value

    @model_validator(mode="after")
    def validate_signup(self) -> Self:
        if self.password.get_secret_value() != self.confirm_password.get_secret_value():
            raise ValueError("Passwords do not match")

        if not self.accept_terms:
            raise ValueError("You must accept the terms and conditions")

        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    is_verified: bool


#  login user schema
class SigninRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserSigninResponse(BaseModel):
    id: str
    email: EmailStr
    token: TokenResponse
