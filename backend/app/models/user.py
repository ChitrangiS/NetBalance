from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    Represents a registered user in the system.
    
    Inherits from both Base (ORM machinery) and TimestampMixin
    (created_at, updated_at columns).
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,         # No two users can share an email
        index=True,          # Fast lookups by email during login
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,        # New users are active by default
        nullable=False,
    )

    # Relationships defined in later steps:
    # group_memberships = relationship("GroupMember", back_populates="user")
    # expenses_paid = relationship("Expense", back_populates="paid_by_user")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"