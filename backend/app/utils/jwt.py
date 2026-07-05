import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")

# Short-lived access token — if stolen, attacker has at most this window
ACCESS_TOKEN_EXPIRE_MINUTES = 15

# Long-lived refresh token — represents an active session
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire, "type": "access"})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token_string() -> str:
    """
    Generate a cryptographically random refresh token string.

    Unlike access tokens (JWTs with a verifiable signature), refresh
    tokens are OPAQUE — they carry no payload, just random bytes.
    Validation works by looking them up in the database (not by
    verifying a signature), which is what gives us revocability.

    secrets.token_urlsafe(32) gives 256 bits of entropy from
    os.urandom() — not predictable or brute-forceable.
    """
    return secrets.token_urlsafe(32)


def create_token_pair(db: Session, user_id: int) -> dict[str, str]:
    """
    Issue a new (access_token, refresh_token) pair for a user.
    Stores the refresh token in the database for future validation.

    Called on:
    - Login (initial issuance)
    - Refresh (rotation — new pair replaces the old refresh token)
    """
    from app.models.refresh_token import RefreshToken

    access_token = create_access_token({"sub": str(user_id)})
    refresh_token_str = create_refresh_token_string()

    refresh_token_db = RefreshToken(
        token=refresh_token_str,
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_token_db)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
    }


def rotate_refresh_token(db: Session, old_refresh_token: str) -> dict[str, str]:
    """
    REFRESH TOKEN ROTATION:
    1. Validate the presented refresh token
    2. If valid → revoke it and issue a new token pair
    3. If already revoked → REUSE DETECTED: revoke ALL tokens for this
       user (sign out all sessions, attacker gets nothing)
    4. If expired or not found → reject

    This pattern is called "refresh token rotation with reuse detection"
    and is the production-standard approach.
    """
    from app.models.refresh_token import RefreshToken
    from sqlalchemy import select

    stmt = select(RefreshToken).where(RefreshToken.token == old_refresh_token)
    token_record = db.execute(stmt).scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # REUSE DETECTION: if this token was already rotated (revoked) and
    # is being presented again, an attacker has a copy of an old token.
    # Revoke ALL sessions for this user immediately.
    if token_record.is_revoked:
        _revoke_all_user_tokens(db, token_record.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected. All sessions have been revoked.",
        )

    if token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired. Please log in again.",
        )

    # Valid, non-expired, non-revoked: revoke this token and issue a new pair
    token_record.is_revoked = True
    db.commit()

    return create_token_pair(db, token_record.user_id)


def _revoke_all_user_tokens(db: Session, user_id: int) -> None:
    """Revoke every active refresh token for a user — used on reuse detection."""
    from app.models.refresh_token import RefreshToken
    from sqlalchemy import update

    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
        .values(is_revoked=True)
    )
    db.commit()


def verify_token(token: str) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return TokenData(user_id=int(user_id))
    except JWTError:
        raise credentials_exception


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from app.models.user import User
    token_data = verify_token(token)
    user = db.get(User, token_data.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user