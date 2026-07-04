from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime


# ── Request Schemas (what the client sends) ───────────────────────────────────

class UserRegister(BaseModel):
    """Validates the registration request body."""
    email: EmailStr                          # Pydantic validates email format
    full_name: str = Field(
        min_length=2,
        max_length=100,
        examples=["Alice Johnson"],
    )
    password: str = Field(
        min_length=8,
        max_length=100,
        examples=["securepassword123"],
    )


class UserLogin(BaseModel):
    """Validates the login request body."""
    email: EmailStr
    password: str


# ── Response Schemas (what the server sends back) ─────────────────────────────

class UserResponse(BaseModel):
    """
    Safe user representation — never includes hashed_password.
    
    model_config = ConfigDict(from_attributes=True) enables
    Pydantic to read data from SQLAlchemy model instances.
    Without this, Pydantic only reads from dicts.
    
    Old Pydantic v1 syntax was: class Config: orm_mode = True
    Pydantic v2 renamed this to from_attributes.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT response returned after successful login."""
    access_token: str
    token_type: str = "bearer"    # OAuth2 standard: always "bearer"


class TokenData(BaseModel):
    """
    Decoded JWT payload — used internally when verifying tokens.
    Not sent to clients.
    """
    user_id: int | None = None