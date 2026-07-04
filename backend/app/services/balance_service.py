from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.expense import Expense, ExpenseSplit
from app.models.group import GroupMember
from app.models.user import User
from app.schemas.balance import MemberBalance, GroupBalanceResponse

ZERO_TOLERANCE = Decimal("0.01")


def _compute_raw_balances(db: Session, group_id: int) -> dict[int, Decimal]:
    """
    Internal, reusable core: returns {user_id: net_balance} for a group.

    This is the SINGLE SOURCE OF TRUTH for balance math. Both the public
    API endpoint (calculate_group_balances) and the settlement algorithm
    (Step 8) call this function — no duplicated aggregation logic.
    """
    members = _get_group_members_with_users(db, group_id)

    paid_stmt = (
        select(Expense.paid_by, func.sum(Expense.amount))
        .where(Expense.group_id == group_id)
        .group_by(Expense.paid_by)
    )
    total_paid_by_user = dict(db.execute(paid_stmt).all())

    owed_stmt = (
        select(ExpenseSplit.user_id, func.sum(ExpenseSplit.amount))
        .join(Expense, ExpenseSplit.expense_id == Expense.id)
        .where(Expense.group_id == group_id)
        .group_by(ExpenseSplit.user_id)
    )
    total_owed_by_user = dict(db.execute(owed_stmt).all())

    raw_balances: dict[int, Decimal] = {}
    for member_user in members:
        paid = total_paid_by_user.get(member_user.id, Decimal("0.00"))
        owed = total_owed_by_user.get(member_user.id, Decimal("0.00"))
        raw_balances[member_user.id] = paid - owed

    return raw_balances


def calculate_group_balances(
    db: Session, group_id: int, current_user: User
) -> GroupBalanceResponse:
    """Public-facing balance calculation — used by the API endpoint."""
    _assert_group_member(db, current_user.id, group_id)

    members = _get_group_members_with_users(db, group_id)
    member_by_id = {m.id: m for m in members}

    raw_balances = _compute_raw_balances(db, group_id)

    # We also need paid/owed breakdowns for display, so recompute those
    # (cheap — same indexed aggregate queries, run once per request)
    paid_stmt = (
        select(Expense.paid_by, func.sum(Expense.amount))
        .where(Expense.group_id == group_id)
        .group_by(Expense.paid_by)
    )
    total_paid_by_user = dict(db.execute(paid_stmt).all())

    owed_stmt = (
        select(ExpenseSplit.user_id, func.sum(ExpenseSplit.amount))
        .join(Expense, ExpenseSplit.expense_id == Expense.id)
        .where(Expense.group_id == group_id)
        .group_by(ExpenseSplit.user_id)
    )
    total_owed_by_user = dict(db.execute(owed_stmt).all())

    balances: list[MemberBalance] = []
    for user_id, net in raw_balances.items():
        member_user = member_by_id[user_id]
        balances.append(MemberBalance(
            user_id=user_id,
            full_name=member_user.full_name,
            email=member_user.email,
            total_paid=total_paid_by_user.get(user_id, Decimal("0.00")),
            total_owed=total_owed_by_user.get(user_id, Decimal("0.00")),
            net_balance=net,
        ))

    balances.sort(key=lambda b: b.net_balance, reverse=True)
    is_settled = all(abs(b.net_balance) < ZERO_TOLERANCE for b in balances)

    return GroupBalanceResponse(group_id=group_id, balances=balances, is_settled=is_settled)


def _assert_group_member(db: Session, user_id: int, group_id: int) -> None:
    stmt = select(GroupMember).where(
        GroupMember.user_id == user_id,
        GroupMember.group_id == group_id,
    )
    if db.execute(stmt).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )


def _get_group_members_with_users(db: Session, group_id: int) -> list[User]:
    stmt = (
        select(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
    )
    return list(db.execute(stmt).scalars().all())