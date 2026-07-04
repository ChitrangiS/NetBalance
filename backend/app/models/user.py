from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────

    created_groups: Mapped[list["Group"]] = relationship(   # type: ignore[name-defined]
        "Group",
        foreign_keys="Group.created_by",
        back_populates="creator",
    )

    group_memberships: Mapped[list["GroupMember"]] = relationship(  # type: ignore[name-defined]
        "GroupMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Expenses this user paid for (they fronted the money)
    expenses_paid: Mapped[list["Expense"]] = relationship(  # type: ignore[name-defined]
        "Expense",
        foreign_keys="Expense.paid_by",
        back_populates="paid_by_user",
    )

    # This user's share rows across all expenses
    expense_splits: Mapped[list["ExpenseSplit"]] = relationship(    # type: ignore[name-defined]
        "ExpenseSplit",
        back_populates="user",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"