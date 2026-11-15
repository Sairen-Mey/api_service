"""Pydantic schemas for the four authentication operations."""

import string

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


ALLOWED_SPECIAL = set(string.punctuation) - set('@"\'<>')
ALLOWED_CHARACTERS = set(string.ascii_letters + string.digits) | ALLOWED_SPECIAL


def validate_new_password(value: str) -> str:
    if (
        not any(c in string.ascii_lowercase for c in value)
        or not any(c in string.ascii_uppercase for c in value)
        or not any(c in string.digits for c in value)
        or not any(c in ALLOWED_SPECIAL for c in value)
        or any(c not in ALLOWED_CHARACTERS for c in value)
    ):
        raise ValueError(
            "Password must include upper/lowercase letters, a digit, "
            "and an allowed special character (not @, \" , ', < or >)."
        )
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=24)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_new_password(value)


class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=24)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_new_password(value)
