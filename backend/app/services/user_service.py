from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserRegister
from app.utils.hashing import hash_password, verify_password
from fastapi import HTTPException, status


def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Fetch a user by email address.
    
    We use SQLAlchemy 2.0 style: db.execute(select(Model).where(...))
    Old 1.x style was: db.query(Model).filter(...).first()
    Both work, but 2.0 style is consistent with async SQLAlchemy.
    """
    stmt = select(User).where(User.email == email)
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Fetch a user by primary key. db.get() is optimized for PK lookups."""
    return db.get(User, user_id)


def create_user(db: Session, user_data: UserRegister) -> User:
    """
    Register a new user.
    
    Steps:
    1. Check email isn't already taken
    2. Hash the password (NEVER store plaintext)
    3. Create the ORM object
    4. Add to session (staged, not yet in DB)
    5. Commit (writes to DB)
    6. Refresh (re-reads from DB to get server-generated values like id, created_at)
    """
    # Step 1: duplicate email check
    existing = get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Step 2: hash password
    hashed = hash_password(user_data.password)

    # Step 3: create ORM object
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed,
    )

    # Steps 4-6: persist to database
    db.add(user)
    db.commit()
    db.refresh(user)    # ← populates user.id, user.created_at from DB

    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Verify credentials and return the user if valid.
    
    Security note: we always call verify_password() even if the user
    doesn't exist. This prevents timing attacks where an attacker
    measures response time to determine if an email is registered.
    (verify_password takes ~250ms; skipping it for unknown emails
    would return ~1ms, revealing which emails exist.)
    """
    user = get_user_by_email(db, email)

    dummy_hash = "$2b$12$DUzZq6ahzDHzSyI8z7b1g.zcTDof//wmzXp8eH0et0kOXjyNgMnnS"
    password_to_check = user.hashed_password if user else dummy_hash
    password_valid = verify_password(password, password_to_check)

    if not user or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",  # Intentionally vague
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user