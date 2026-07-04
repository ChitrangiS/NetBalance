from app.models.base import Base, TimestampMixin
from app.models.user import User   # ← Alembic now discovers this table

__all__ = ["Base", "TimestampMixin", "User"]