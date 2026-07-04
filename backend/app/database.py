from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# The engine is the entry point to the database.
# It manages the connection pool and knows how to speak to PostgreSQL.
# pool_pre_ping=True: before handing out a connection from the pool,
# SQLAlchemy sends a cheap "SELECT 1" to verify it's still alive.
# This prevents "connection already closed" errors after Postgres restarts.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,        # Keep 5 connections open at all times
    max_overflow=10,    # Allow 10 extra connections under heavy load
    echo=False,         # Set True to log every SQL query (useful for debugging)
)

# ── Session Factory ───────────────────────────────────────────────────────────
# SessionLocal is a factory — calling SessionLocal() creates a new Session.
# autocommit=False: we control when transactions commit (safest default)
# autoflush=False:  we control when pending changes are sent to DB
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Dependency ────────────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    
    The 'yield' makes this a generator — code after yield runs
    after the request finishes (like a finally block).
    
    This guarantees the session is always closed, even if an exception
    is raised mid-request. No connection leaks.
    
    Usage in a route:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db          # ← request handler runs here
    finally:
        db.close()        # ← always runs, even on exception