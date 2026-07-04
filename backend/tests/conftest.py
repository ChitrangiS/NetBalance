import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from typing import Generator

from app.main import app
from app.database import get_db
from app.models import Base


# ── In-memory SQLite for tests ────────────────────────────────────────────────
# We do NOT test against the real PostgreSQL database.
# Reasons:
#   1. Tests should be isolated — no leftover data between runs
#   2. SQLite in-memory is instant; Postgres requires network + auth
#   3. Tests run in CI without a Postgres server
#
# StaticPool: ensures the same in-memory DB is shared across all
# connections in the same test (SQLite default creates a new DB per connection)
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific requirement
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Creates a fresh database for every test function.
    
    scope="function" means this fixture runs once per test.
    Tables are created before the test and dropped after.
    This guarantees test isolation — no state leaks between tests.
    """
    Base.metadata.create_all(bind=engine)   # Create all tables
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)  # Clean up after test


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Provides a TestClient with the test DB injected.
    
    FastAPI's dependency injection lets us swap get_db() for
    our test version. This is the correct way to test FastAPI apps.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Session managed by the db fixture above

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()   # Clean up overrides after test