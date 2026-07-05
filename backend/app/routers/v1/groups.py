from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.jwt import get_current_user
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupJoin,
    GroupResponse,
    GroupDetailResponse,
)
from app.services import group_service

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post(
    "/",
    response_model=GroupDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    group_data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),   # ← protected
):
    """
    Create a new group. The authenticated user becomes the admin.
    """
    group = group_service.create_group(db, group_data, current_user)
    return GroupDetailResponse.from_group(group)


@router.post("/join", response_model=GroupDetailResponse)
def join_group(
    join_data: GroupJoin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join an existing group using its invite code."""
    group = group_service.join_group(db, join_data.invite_code, current_user)
    return GroupDetailResponse.from_group(group)


@router.get("/", response_model=list[GroupResponse])
def list_my_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all groups the current user belongs to."""
    groups = group_service.get_user_groups(db, current_user)
    return [GroupResponse.from_group(g) for g in groups]


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get full group details including member list.
    Returns 403 if the requester is not a member.
    """
    group = group_service.get_group_by_id(db, group_id, current_user)
    return GroupDetailResponse.from_group(group)