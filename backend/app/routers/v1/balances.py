from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.jwt import get_current_user
from app.models.user import User
from app.schemas.balance import GroupBalanceResponse
from app.services import balance_service

router = APIRouter(prefix="/groups/{group_id}/balances", tags=["balances"])


@router.get("/", response_model=GroupBalanceResponse)
def get_group_balances(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get every member's net balance for this group.

    net_balance > 0 → owed money
    net_balance < 0 → owes money
    """
    return balance_service.calculate_group_balances(db, group_id, current_user)