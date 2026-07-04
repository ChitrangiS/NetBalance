from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.jwt import get_current_user
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseSummary
from app.services import expense_service

# Note the nested prefix — expenses always live under a group
router = APIRouter(prefix="/groups/{group_id}/expenses", tags=["expenses"])


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    group_id: int,
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record a new expense in the group.

    The authenticated user is automatically recorded as the payer.
    split_with determines who shares the cost (for EQUAL splits).
    """
    expense = expense_service.create_expense(db, group_id, expense_data, current_user)
    return ExpenseResponse.from_expense(expense)


@router.get("/", response_model=list[ExpenseSummary])
def list_expenses(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all expenses in a group, newest first."""
    expenses = expense_service.get_group_expenses(db, group_id, current_user)
    return [ExpenseSummary.from_expense(e) for e in expenses]


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    group_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of one expense, including per-person splits."""
    expense = expense_service.get_expense_by_id(db, group_id, expense_id, current_user)
    return ExpenseResponse.from_expense(expense)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    group_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an expense. Only the payer or a group admin can do this.
    Returns 204 No Content on success — no body.
    """
    expense_service.delete_expense(db, group_id, expense_id, current_user)