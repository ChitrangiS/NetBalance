from decimal import Decimal, ROUND_DOWN
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.expense import Expense, ExpenseSplit, SplitType
from app.models.group import GroupMember
from app.models.user import User
from app.schemas.expense import ExpenseCreate


# ── Split calculation ──────────────────────────────────────────────────────────

def calculate_equal_splits(
    amount: Decimal,
    user_ids: list[int],
    payer_id: int,
) -> dict[int, Decimal]:
    """
    Divide `amount` equally among `user_ids`, guaranteeing the
    shares sum to EXACTLY `amount` — no floating point drift,
    no missing or extra paisa.

    Algorithm (largest-remainder method):
      1. base_share = floor(amount / count) to 2 decimal places
      2. remainder  = amount - (base_share * count)
      3. give the remainder (in 0.01 increments) to the payer first
         (deterministic, simple, and the payer "absorbs" the odd cent
         since they fronted the money anyway)

    Returns: {user_id: share_amount}
    """
    count = len(user_ids)
    if count == 0:
        raise ValueError("Cannot split among zero people")

    # Step 1 — base share, rounded DOWN to avoid overshooting the total
    base_share = (amount / count).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    # Step 2 — remainder left after giving everyone the base share
    total_base = base_share * count
    remainder = amount - total_base   # always >= 0 because we rounded DOWN

    shares: dict[int, Decimal] = {uid: base_share for uid in user_ids}

    # Step 3 — give the remainder to the payer, in 1-cent increments
    # (remainder is at most `count - 1` cents, e.g. splitting among 3
    #  people the remainder can never reach a full extra cent for everyone)
    cents_remaining = int((remainder * 100).to_integral_value())
    one_cent = Decimal("0.01")

    if payer_id in shares:
        shares[payer_id] += one_cent * cents_remaining
    else:
        # Payer isn't part of the split (rare: paid for others entirely) —
        # give remainder to the first user_id deterministically instead
        first_uid = user_ids[0]
        shares[first_uid] += one_cent * cents_remaining

    return shares


def calculate_exact_splits(splits_input: list) -> dict[int, Decimal]:
    """EXACT split: amounts are provided directly by the caller (pre-validated by schema)."""
    return {s.user_id: s.amount for s in splits_input}


def calculate_percentage_splits(
    amount: Decimal,
    splits_input: list,
) -> dict[int, Decimal]:
    """
    PERCENTAGE split: convert percentages to amounts.
    Uses the same largest-remainder approach to avoid rounding drift.
    """
    raw_shares: dict[int, Decimal] = {}
    for s in splits_input:
        share = (amount * s.percentage / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        raw_shares[s.user_id] = share

    total = sum(raw_shares.values())
    remainder = amount - total
    cents_remaining = int((remainder * 100).to_integral_value())

    # Give remainder cents to the first user(s), one cent each, deterministically
    one_cent = Decimal("0.01")
    user_ids = list(raw_shares.keys())
    for i in range(cents_remaining):
        raw_shares[user_ids[i % len(user_ids)]] += one_cent

    return raw_shares


# ── Authorization helpers ──────────────────────────────────────────────────────

def _assert_group_member(db: Session, user_id: int, group_id: int) -> None:
    """Raise 403 if user_id is not a member of group_id."""
    stmt = select(GroupMember).where(
        GroupMember.user_id == user_id,
        GroupMember.group_id == group_id,
    )
    membership = db.execute(stmt).scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )


def _get_group_member_ids(db: Session, group_id: int) -> set[int]:
    """Fetch the set of user_ids who belong to this group."""
    stmt = select(GroupMember.user_id).where(GroupMember.group_id == group_id)
    return set(db.execute(stmt).scalars().all())


# ── CRUD operations ────────────────────────────────────────────────────────────

def create_expense(
    db: Session,
    group_id: int,
    expense_data: ExpenseCreate,
    current_user: User,
) -> Expense:
    """
    Create an expense and its splits atomically.

    Steps:
    1. Authorization: current_user must be a group member
    2. Validate every user in split_with is also a group member
       (and the payer too)
    3. Calculate shares based on split_type
    4. Insert Expense + all ExpenseSplit rows in one transaction
    """
    # 1. Authorization
    _assert_group_member(db, current_user.id, group_id)

    # 2. Validate all referenced users are group members
    group_member_ids = _get_group_member_ids(db, group_id)

    if current_user.id not in group_member_ids:
        # Defensive — should already be caught by _assert_group_member
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a group member")

    invalid_users = set(expense_data.split_with) - group_member_ids
    if invalid_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User(s) {invalid_users} are not members of this group",
        )

    # 3. Calculate shares
    if expense_data.split_type == SplitType.EQUAL:
        shares = calculate_equal_splits(
            amount=expense_data.amount,
            user_ids=expense_data.split_with,
            payer_id=current_user.id,
        )
    elif expense_data.split_type == SplitType.EXACT:
        # Schema already validated splits sum to amount
        shares = calculate_exact_splits(expense_data.splits)
        # Also validate those user_ids are group members
        invalid = set(shares.keys()) - group_member_ids
        if invalid:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"User(s) {invalid} are not members of this group",
            )
    elif expense_data.split_type == SplitType.PERCENTAGE:
        shares = calculate_percentage_splits(expense_data.amount, expense_data.splits)
        invalid = set(shares.keys()) - group_member_ids
        if invalid:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"User(s) {invalid} are not members of this group",
            )
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown split type")

    # Final safety check — defense in depth, even though calculation
    # functions are designed to be exact
    total_shares = sum(shares.values())
    if total_shares != expense_data.amount:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal split calculation error — totals do not match",
        )

    # 4. Persist — Expense + all ExpenseSplit rows, single transaction
    expense = Expense(
        group_id=group_id,
        paid_by=current_user.id,
        amount=expense_data.amount,
        description=expense_data.description,
        notes=expense_data.notes,
        split_type=expense_data.split_type,
    )
    db.add(expense)
    db.flush()   # get expense.id without committing yet

    for user_id, share_amount in shares.items():
        percentage = None
        if expense_data.split_type == SplitType.PERCENTAGE and expense_data.splits:
            matching = next(
                (s for s in expense_data.splits if s.user_id == user_id), None
            )
            percentage = matching.percentage if matching else None

        db.add(ExpenseSplit(
            expense_id=expense.id,
            user_id=user_id,
            amount=share_amount,
            percentage=percentage,
        ))

    db.commit()
    db.refresh(expense)

    return _load_expense_with_relations(db, expense.id)


def get_group_expenses(
    db: Session,
    group_id: int,
    current_user: User,
) -> list[Expense]:
    """List all expenses for a group, newest first."""
    _assert_group_member(db, current_user.id, group_id)

    stmt = (
    select(Expense)
    .where(Expense.group_id == group_id)
    .options(selectinload(Expense.paid_by_user))
    .order_by(
        Expense.created_at.desc(),
        Expense.id.desc(),   # tie-breaker
    )
)
    return list(db.execute(stmt).scalars().all())


def get_expense_by_id(
    db: Session,
    group_id: int,
    expense_id: int,
    current_user: User,
) -> Expense:
    """Get one expense with full split details."""
    _assert_group_member(db, current_user.id, group_id)

    expense = _load_expense_with_relations(db, expense_id)

    if not expense or expense.group_id != group_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found in this group",
        )

    return expense


def delete_expense(
    db: Session,
    group_id: int,
    expense_id: int,
    current_user: User,
) -> None:
    """
    Delete an expense (and cascade-delete its splits).

    Authorization: only the person who PAID can delete it,
    OR a group admin. Regular members cannot delete others' expenses.
    """
    _assert_group_member(db, current_user.id, group_id)

    expense = db.get(Expense, expense_id)
    if not expense or expense.group_id != group_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found in this group",
        )

    is_payer = expense.paid_by == current_user.id
    is_admin = _is_group_admin(db, current_user.id, group_id)

    if not (is_payer or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the payer or a group admin can delete this expense",
        )

    db.delete(expense)   # cascade deletes splits automatically
    db.commit()


def _is_group_admin(db: Session, user_id: int, group_id: int) -> bool:
    from app.models.group import MemberRole
    stmt = select(GroupMember).where(
        GroupMember.user_id == user_id,
        GroupMember.group_id == group_id,
        GroupMember.role == MemberRole.ADMIN,
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def _load_expense_with_relations(db: Session, expense_id: int) -> Expense | None:
    stmt = (
        select(Expense)
        .where(Expense.id == expense_id)
        .options(
            selectinload(Expense.paid_by_user),
            selectinload(Expense.splits),
        )
    )
    return db.execute(stmt).scalar_one_or_none()