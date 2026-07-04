from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func


class Base(DeclarativeBase):
    """
    All ORM models inherit from this class.
    DeclarativeBase is the SQLAlchemy 2.0 way to define the Base.
    (replaces the old: Base = declarative_base())
    """
    pass


class TimestampMixin:
    """
    Mixin adds created_at and updated_at to any model that inherits it.
    
    A mixin is a class that provides reusable functionality without
    being a standalone class. Python supports multiple inheritance,
    so a model can inherit from both Base and TimestampMixin.
    
    server_default=func.now(): the DATABASE sets the timestamp,
    not Python. This is safer — Python's clock can drift across
    multiple backend instances, but the DB has one authoritative clock.
    
    onupdate=func.now(): automatically updates whenever the row changes.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )