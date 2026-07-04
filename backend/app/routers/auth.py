from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserRegister, UserResponse, TokenResponse, UserLogin
from app.services.user_service import create_user, authenticate_user
from app.utils.jwt import create_access_token, get_current_user
from app.models.user import User

# APIRouter groups related endpoints.
# prefix="/auth" means all routes here start with /auth
# tags=["auth"] groups them in the /docs UI
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,   # 201 Created, not 200 OK
)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    FastAPI automatically:
    - Parses the JSON body into UserRegister
    - Validates email format, password length, etc.
    - Returns 422 Unprocessable Entity if validation fails
    
    response_model=UserResponse ensures hashed_password
    is NEVER included in the response, even if we accidentally
    return the full User ORM object.
    """
    user = create_user(db, user_data)
    return user


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate and return a JWT token.
    
    The token payload uses "sub" (subject) — the RFC 7519 standard claim.
    We store user_id as a string in "sub" because JWT claims are strings.
    """
    user = authenticate_user(db, credentials.email, credentials.password)

    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Return the currently authenticated user's profile.
    
    This is a protected route — FastAPI calls get_current_user()
    before calling this function. If the token is missing or invalid,
    get_current_user() raises HTTP 401 and this function never runs.
    """
    return current_user