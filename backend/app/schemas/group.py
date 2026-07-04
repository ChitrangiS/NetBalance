from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from app.models.group import MemberRole


# ── Request Schemas ───────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100, examples=["Trip to Goa"])
    description: str | None = Field(
        default=None,
        max_length=500,
        examples=["Our annual trip"],
    )


class GroupJoin(BaseModel):
    invite_code: str = Field(
        min_length=1,
        max_length=12,
        examples=["a3f9kx8b"],
    )


# ── Response Schemas ──────────────────────────────────────────────────────────

class MemberResponse(BaseModel):
    """A single member's info as seen from inside a group."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str      # Pulled from the nested user relationship
    email: str
    role: MemberRole
    joined_at: datetime

    @classmethod
    def from_membership(cls, membership: "GroupMember") -> "MemberResponse":  # type: ignore[name-defined]
        """
        Custom factory: GroupMember has a nested .user relationship.
        We flatten it for the response so clients get one clean object.
        """
        return cls(
            user_id=membership.user_id,
            full_name=membership.user.full_name,
            email=membership.user.email,
            role=membership.role,
            joined_at=membership.created_at,
        )


class GroupResponse(BaseModel):
    """Group details returned to clients."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    invite_code: str
    created_by: int
    member_count: int
    created_at: datetime

    @classmethod
    def from_group(cls, group: "Group") -> "GroupResponse":  # type: ignore[name-defined]
        return cls(
            id=group.id,
            name=group.name,
            description=group.description,
            invite_code=group.invite_code,
            created_by=group.created_by,
            member_count=len(group.memberships),
            created_at=group.created_at,
        )


class GroupDetailResponse(GroupResponse):
    """
    Extended group response that includes the full member list.
    Returned only for single-group detail views.
    
    Inherits all fields from GroupResponse and adds members.
    """
    members: list[MemberResponse]

    @classmethod
    def from_group(cls, group: "Group") -> "GroupDetailResponse":  # type: ignore[name-defined]
        return cls(
            id=group.id,
            name=group.name,
            description=group.description,
            invite_code=group.invite_code,
            created_by=group.created_by,
            member_count=len(group.memberships),
            created_at=group.created_at,
            members=[
                MemberResponse.from_membership(m)
                for m in group.memberships
            ],
        )