from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.group import Group, GroupMember, MemberRole
from app.models.user import User
from app.schemas.group import GroupCreate


def create_group(db: Session, group_data: GroupCreate, creator: User) -> Group:
    """
    Create a new group and automatically add the creator as admin.
    
    Both operations happen in a single transaction.
    If adding the creator as member fails, the group creation
    is also rolled back — no orphaned empty groups.
    """
    group = Group(
        name=group_data.name,
        description=group_data.description,
        invite_code=Group.generate_invite_code(),
        created_by=creator.id,
    )
    db.add(group)
    db.flush()
    # flush() sends the INSERT to the DB within the current transaction
    # but does NOT commit. This gives us group.id for the next step
    # without permanently committing yet.

    # Automatically make the creator an admin member
    membership = GroupMember(
        user_id=creator.id,
        group_id=group.id,
        role=MemberRole.ADMIN,
    )
    db.add(membership)
    db.commit()

    # Eager load memberships so GroupResponse can count them
    db.refresh(group)
    _load_group_with_members(db, group.id)

    return get_group_by_id(db, group.id, creator)


def join_group(db: Session, invite_code: str, user: User) -> Group:
    """
    Add a user to a group via invite code.
    
    Checks:
    1. Invite code must exist
    2. User must not already be a member
    """
    # Find group by invite code
    stmt = (
        select(Group)
        .where(Group.invite_code == invite_code)
        .options(selectinload(Group.memberships).selectinload(GroupMember.user))
    )
    group = db.execute(stmt).scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code",
        )

    # Check if already a member
    existing = _get_membership(db, user.id, group.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this group",
        )

    membership = GroupMember(
        user_id=user.id,
        group_id=group.id,
        role=MemberRole.MEMBER,
    )
    db.add(membership)
    db.commit()

    return get_group_by_id(db, group.id, user)


def get_user_groups(db: Session, user: User) -> list[Group]:
    """
    Return all groups the user is a member of.
    
    Query path:
      GroupMember (filter by user_id)
        → Group (join)
          → GroupMember list (selectinload for member_count)
    
    selectinload fires a second SELECT ... WHERE group_id IN (...)
    This is the "select in" strategy — 2 queries total, not N+1.
    """
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user.id)
        .options(selectinload(Group.memberships))
        .order_by(Group.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_group_by_id(db: Session, group_id: int, user: User) -> Group:
    """
    Fetch a single group with full member details.
    
    Authorization: user must be a member of this group.
    We enforce this here in the service layer, not just the route.
    This means even internal service calls can't bypass the check.
    """
    stmt = (
        select(Group)
        .where(Group.id == group_id)
        .options(
            selectinload(Group.memberships).selectinload(GroupMember.user)
            # selectinload chaining: load memberships AND for each membership load its user
            # Generates 2 queries:
            #   SELECT * FROM group_members WHERE group_id = ?
            #   SELECT * FROM users WHERE id IN (?, ?, ?, ...)
        )
    )
    group = db.execute(stmt).scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # Authorization check
    membership = _get_membership(db, user.id, group_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    return group


def _get_membership(
    db: Session,
    user_id: int,
    group_id: int,
) -> GroupMember | None:
    """
    Internal helper — check if a user is in a group.
    Prefixed with _ to signal it's private to this module.
    """
    stmt = select(GroupMember).where(
        GroupMember.user_id == user_id,
        GroupMember.group_id == group_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def _load_group_with_members(db: Session, group_id: int) -> Group | None:
    """Internal helper to eagerly load a group with all member data."""
    stmt = (
        select(Group)
        .where(Group.id == group_id)
        .options(
            selectinload(Group.memberships).selectinload(GroupMember.user)
        )
    )
    return db.execute(stmt).scalar_one_or_none()