from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app.utils.jwt import get_current_user
from app.models.user import User
from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseSummary
from app.schemas.pagination import PaginatedResponse, make_paginated_response
from app.services import expense_service

router = APIRouter(prefix="/groups/{group_id}/expenses", tags=["expenses"])


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    group_id: int,
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = expense_service.create_expense(db, group_id, expense_data, current_user)
    return ExpenseResponse.from_expense(expense)


@router.get("/", response_model=PaginatedResponse[ExpenseSummary])
def list_expenses(
    group_id: int,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List group expenses with offset pagination.

    page and page_size are query parameters with validation:
    - ge=1: page must be >= 1 (no page 0 or negative pages)
    - le=100: page_size cannot exceed 100 (prevents "give me all 10,000
      records" abuse hiding behind a large page_size parameter)

    We run TWO queries:
    1. COUNT(*) — gets the total for pagination metadata
    2. SELECT with LIMIT/OFFSET — gets the actual page of data

    Both are fast because group_id is indexed.
    """
    from app.services.expense_service import _assert_group_member
    from sqlalchemy.orm import selectinload

    _assert_group_member(db, current_user.id, group_id)

    # Query 1: total count (no LIMIT/OFFSET — we need the FULL count)
    count_stmt = (
        select(func.count())
        .select_from(Expense)
        .where(Expense.group_id == group_id)
    )
    total = db.execute(count_stmt).scalar_one()

    # Query 2: the actual page
    offset = (page - 1) * page_size
    stmt = (
        select(Expense)
        .where(Expense.group_id == group_id)
        .options(selectinload(Expense.paid_by_user))
        .order_by(Expense.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )
    expenses = list(db.execute(stmt).scalars().all())

    items = [ExpenseSummary.from_expense(e) for e in expenses]

    return make_paginated_response(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    group_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = expense_service.get_expense_by_id(db, group_id, expense_id, current_user)
    return ExpenseResponse.from_expense(expense)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    group_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense_service.delete_expense(db, group_id, expense_id, current_user)