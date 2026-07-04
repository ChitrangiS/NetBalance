from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.user import TokenData

# OAuth2PasswordBearer tells FastAPI:
# "Tokens arrive in the Authorization: Bearer <token> header"
# "The login endpoint that issues tokens is at /auth/login"
# This also makes the /docs UI show an Authorize button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict[str, Any]) -> str:
    """
    Create a signed JWT token.
    
    We copy `data` before modifying it — never mutate function arguments.
    We set expiry to UTC now + configured minutes.
    jose.jwt.encode() signs with SECRET_KEY using HS256 algorithm.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expire})    # "exp" is the standard JWT expiry claim

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def verify_token(token: str) -> TokenData:
    """
    Decode and verify a JWT token.
    
    Raises HTTP 401 if:
    - Token signature is invalid (tampered)
    - Token is expired
    - Token doesn't contain expected claims
    
    We raise the same generic error for all failures —
    don't tell attackers WHY their token failed.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},  # OAuth2 standard header
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],  # List — allows multiple algorithms
        )
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
    """
    FastAPI dependency — extracts and returns the current logged-in user.
    
    Used in protected routes:
        @router.get("/me")
        def get_me(current_user = Depends(get_current_user)):
            return current_user
    
    FastAPI resolves dependency chains automatically:
    get_current_user → depends on oauth2_scheme (extracts token from header)
                     → depends on get_db (provides DB session)
    """
    from app.models.user import User   # local import avoids circular imports

    token_data = verify_token(token)

    user = db.get(User, token_data.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user