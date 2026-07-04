import enum
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Numeric, String, Text, ForeignKey,
    Enum as SAEnum, CheckConstraint, UniqueConstraint,
    Integer,
)
from app.models.base import Base, TimestampMixin


class SplitType(str, enum.Enum):
    """
    How the expense amount is divided among members.

    EQUAL:      divide total evenly — ₹900 among 3 = ₹300 each
    EXACT:      specify each person's exact amount — ₹500, ₹300, ₹100
    PERCENTAGE: specify percentages — 50%, 30%, 20%

    str mixin ensures JSON serialization gives "equal" not "SplitType.EQUAL"
    """
    EQUAL = "equal"
    EXACT = "exact"
    PERCENTAGE = "percentage"


class Expense(Base, TimestampMixin):
    """
    Records a single payment made by one group member on behalf of the group.

    One Expense → many ExpenseSplits (one per member who shares the cost).

    The payer is recorded in paid_by. Their own share appears as an
    ExpenseSplit row just like every other member — this keeps the
    balance calculation uniform (net = paid - owed for everyone).
    """
    __tablename__ = "expenses"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_expenses_amount_positive",
        ),
        # name= is required so Alembic can track this constraint
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"),
        # If the group is deleted, all its expenses are deleted too
        nullable=False,
        index=True,        # We frequently filter expenses by group
    )

    paid_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        # RESTRICT: can't delete a user who paid expenses
        # We need their record for historical accuracy
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        # precision=10: up to 10 significant digits total
        # scale=2:      exactly 2 decimal places
        # Max storable: 99,999,999.99
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,             # TEXT: unlimited length (for longer descriptions)
        nullable=True,
    )

    split_type: Mapped[SplitType] = mapped_column(
        SAEnum(SplitType),
        nullable=False,
        default=SplitType.EQUAL,
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    group: Mapped["Group"] = relationship(      # type: ignore[name-defined]
        "Group",
        back_populates="expenses",
    )

    paid_by_user: Mapped["User"] = relationship(    # type: ignore[name-defined]
        "User",
        foreign_keys=[paid_by],
        back_populates="expenses_paid",
    )

    splits: Mapped[list["ExpenseSplit"]] = relationship(
        "ExpenseSplit",
        back_populates="expense",
        cascade="all, delete-orphan",
        # If expense is deleted, all its splits are deleted automatically
    )

    def __repr__(self) -> str:
        return (
            f"<Expense id={self.id} "
            f"amount={self.amount} "
            f"description={self.description!r}>"
        )


class ExpenseSplit(Base, TimestampMixin):
    """
    Records one member's share of a single expense.

    For every Expense, there is one ExpenseSplit per member
    who is included in that expense — including the payer.

    Example: Alice pays ₹900 for 3 people
        ExpenseSplit(expense=1, user=alice,  amount=300)
        ExpenseSplit(expense=1, user=bob,    amount=300)
        ExpenseSplit(expense=1, user=carol,  amount=300)

    Constraints:
    - A user can only appear once per expense (UniqueConstraint)
    - Amount must be non-negative (a ₹0 split is valid — e.g., the payer
      explicitly excluded from owing anything)
    - Percentage must be between 0 and 100 (CHECK constraint)
    """
    __tablename__ = "expense_splits"

    __table_args__ = (
        UniqueConstraint(
            "expense_id",
            "user_id",
            name="uq_expense_splits_expense_user",
            # Prevents the same user appearing twice in one expense
        ),
        CheckConstraint(
            "amount >= 0",
            name="ck_expense_splits_amount_non_negative",
        ),
        CheckConstraint(
            "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
            name="ck_expense_splits_percentage_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,      # Frequently queried: "all splits for expense X"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,      # Frequently queried: "all splits owed by user Y"
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
    )

    percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=2),
        # precision=5, scale=2 → max 999.99 (but CHECK constrains to 100)
        nullable=True,    # NULL for EQUAL splits (not needed)
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    expense: Mapped["Expense"] = relationship(
        "Expense",
        back_populates="splits",
    )

    user: Mapped["User"] = relationship(        # type: ignore[name-defined]
        "User",
        foreign_keys=[user_id],
        back_populates="expense_splits",
    )

    def __repr__(self) -> str:
        return (
            f"<ExpenseSplit expense={self.expense_id} "
            f"user={self.user_id} "
            f"amount={self.amount}>"
        )