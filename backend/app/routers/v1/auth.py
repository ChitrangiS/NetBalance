from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserRegister, UserResponse, UserLogin
from app.services.user_service import create_user, authenticate_user
from app.utils.jwt import create_token_pair, rotate_refresh_token, get_current_user
from app.models.user import User
from app.utils.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    user = create_user(db, user_data)
    return user


@router.post("/login", response_model=TokenPairResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
    # Rate limit: 5 attempts per 60 seconds per IP.
    # bcrypt takes ~250ms/attempt — without rate limiting, a bot can
    # try many passwords per second by parallelising across threads.
    # This caps the attempt rate at the HTTP layer, before bcrypt even runs.
    _: None = Depends(rate_limit(limit=5, window_seconds=60)),
):
    user = authenticate_user(db, credentials.email, credentials.password)
    return create_token_pair(db, user.id)


@router.post("/refresh", response_model=TokenPairResponse)
def refresh_tokens(
    body: RefreshRequest,
    db: Session = Depends(get_db),
    # Also rate-limit the refresh endpoint — prevents brute-forcing token values,
    # though the 256-bit entropy makes this more of a defence-in-depth measure
    _: None = Depends(rate_limit(limit=10, window_seconds=60)),
):
    """
    Exchange a valid refresh token for a new (access_token, refresh_token) pair.
    The old refresh token is IMMEDIATELY revoked (rotation).
    If the old token was already revoked, ALL sessions are revoked (reuse detection).
    """
    return rotate_refresh_token(db, body.refresh_token)


@router.post("/logout")
def logout(
    body: RefreshRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke a specific refresh token (log out one session/device).
    The access token remains valid until its 15-minute natural expiry —
    this is the fundamental tradeoff of stateless access tokens.
    For true instant revocation, you'd maintain an access token blocklist.
    """
    from app.models.refresh_token import RefreshToken
    from sqlalchemy import select

    stmt = select(RefreshToken).where(
        RefreshToken.token == body.refresh_token,
        RefreshToken.user_id == current_user.id,
    )
    token_record = db.execute(stmt).scalar_one_or_none()

    if token_record and not token_record.is_revoked:
        token_record.is_revoked = True
        db.commit()

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user