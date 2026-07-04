from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import (
    Expense, ExpenseSplit, SplitType, Group, GroupMember, MemberRole
)
from app.utils.hashing import hash_password
from app.models.user import User


# ── Expense model tests ───────────────────────────────────────────────────────

def test_expense_created_correctly(db, db_expense, db_users, db_group):
    """Expense row has correct values after creation."""
    expense = db_expense

    assert expense.id is not None
    assert expense.amount == Decimal("900.00")
    assert expense.description == "Dinner"
    assert expense.split_type == SplitType.EQUAL
    assert expense.group_id == db_group.id
    assert expense.paid_by == db_users["alice"].id


def test_expense_has_three_splits(db, db_expense):
    """Each group member gets an ExpenseSplit row."""
    assert len(db_expense.splits) == 3


def test_splits_sum_to_expense_total(db, db_expense):
    """
    Core invariant: sum of all splits must equal expense total.
    This is the contract that makes balance calculations correct.
    """
    total_splits = sum(s.amount for s in db_expense.splits)
    assert total_splits == db_expense.amount


def test_each_split_amount_correct(db, db_expense, db_users):
    """Equal split: each person owes exactly ₹300."""
    for split in db_expense.splits:
        assert split.amount == Decimal("300.00")


def test_expense_relationships_loaded(db, db_expense, db_users):
    """paid_by_user relationship resolves to the correct User object."""
    assert db_expense.paid_by_user.email == "alice@x.com"


# ── Constraint tests ──────────────────────────────────────────────────────────

def test_duplicate_split_user_rejected(db, db_expense, db_users):
    """
    Same user cannot have two splits for the same expense.
    UniqueConstraint(expense_id, user_id) must reject this.
    """
    duplicate = ExpenseSplit(
        expense_id=db_expense.id,
        user_id=db_users["alice"].id,
        amount=Decimal("100.00"),
    )
    db.add(duplicate)

    with pytest.raises(IntegrityError):
        db.flush()

    db.rollback()


def test_split_cascade_delete(db, db_expense):
    """
    Deleting an expense must cascade-delete all its splits.
    No orphaned splits should remain.
    """
    expense_id = db_expense.id
    split_count_before = len(db_expense.splits)
    assert split_count_before == 3

    db.delete(db_expense)
    db.commit()

    # Verify splits are gone
    from sqlalchemy import select
    remaining = db.execute(
        select(ExpenseSplit).where(ExpenseSplit.expense_id == expense_id)
    ).scalars().all()
    assert len(remaining) == 0


def test_group_cascade_deletes_expenses(db, db_group, db_expense):
    """
    Deleting a group cascades to expenses and then to splits.
    """
    group_id = db_group.id
    expense_id = db_expense.id

    db.delete(db_group)
    db.commit()

    from sqlalchemy import select
    expenses = db.execute(
        select(Expense).where(Expense.group_id == group_id)
    ).scalars().all()
    splits = db.execute(
        select(ExpenseSplit).where(ExpenseSplit.expense_id == expense_id)
    ).scalars().all()

    assert len(expenses) == 0
    assert len(splits) == 0


# ── Schema validation tests ───────────────────────────────────────────────────

def test_expense_create_schema_equal_split():
    """EQUAL split schema validates correctly with user ids."""
    from app.schemas.expense import ExpenseCreate

    schema = ExpenseCreate(
        description="Dinner",
        amount=Decimal("900.00"),
        split_type=SplitType.EQUAL,
        split_with=[1, 2, 3],
    )
    assert schema.amount == Decimal("900.00")
    assert len(schema.split_with) == 3


def test_expense_create_schema_exact_split_valid():
    """EXACT splits that sum to total pass validation."""
    from app.schemas.expense import ExpenseCreate, SplitInput

    schema = ExpenseCreate(
        description="Dinner",
        amount=Decimal("900.00"),
        split_type=SplitType.EXACT,
        split_with=[1, 2, 3],
        splits=[
            SplitInput(user_id=1, amount=Decimal("500.00")),
            SplitInput(user_id=2, amount=Decimal("300.00")),
            SplitInput(user_id=3, amount=Decimal("100.00")),
        ],
    )
    assert schema.split_type == SplitType.EXACT


def test_expense_create_schema_exact_split_invalid():
    """EXACT splits that don't sum to total fail validation."""
    from app.schemas.expense import ExpenseCreate, SplitInput
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        ExpenseCreate(
            description="Dinner",
            amount=Decimal("900.00"),
            split_type=SplitType.EXACT,
            split_with=[1, 2, 3],
            splits=[
                SplitInput(user_id=1, amount=Decimal("400.00")),
                SplitInput(user_id=2, amount=Decimal("300.00")),
                # Only 700, not 900 — should fail
            ],
        )
    assert "sum" in str(exc_info.value).lower()


def test_expense_create_schema_percentage_must_sum_to_100():
    """Percentages not summing to 100 fail validation."""
    from app.schemas.expense import ExpenseCreate, SplitInput
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ExpenseCreate(
            description="Rent",
            amount=Decimal("30000.00"),
            split_type=SplitType.PERCENTAGE,
            split_with=[1, 2],
            splits=[
                SplitInput(user_id=1, percentage=Decimal("60")),
                SplitInput(user_id=2, percentage=Decimal("30")),
                # 90%, not 100% — should fail
            ],
        )


def test_negative_expense_amount_rejected():
    """Amount must be positive — schema rejects negative values."""
    from app.schemas.expense import ExpenseCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ExpenseCreate(
            description="Negative",
            amount=Decimal("-100.00"),
            split_type=SplitType.EQUAL,
            split_with=[1, 2],
        )