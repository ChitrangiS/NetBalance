from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.jwt import get_current_user
from app.models.user import User
from app.schemas.settlement import SettlementPlanResponse
from app.services import settlement_service

router = APIRouter(prefix="/groups/{group_id}/settlements", tags=["settlements"])


@router.get("/", response_model=SettlementPlanResponse)
def get_settlement_plan(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the minimum-transaction settlement plan for a group.

    Returns the fewest payments needed to bring every member's
    balance to zero, computed via a greedy largest-creditor /
    largest-debtor matching algorithm.
    """
    return settlement_service.calculate_settlement_plan(db, group_id, current_user)