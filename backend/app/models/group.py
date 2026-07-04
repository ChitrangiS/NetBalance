import secrets
import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Enum
from app.models.base import Base, TimestampMixin


class MemberRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class Group(Base, TimestampMixin):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    invite_code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    creator: Mapped["User"] = relationship(     # type: ignore[name-defined]
        "User", foreign_keys=[created_by], back_populates="created_groups"
    )
    memberships: Mapped[list["GroupMember"]] = relationship(
        "GroupMember", back_populates="group", cascade="all, delete-orphan"
    )

    # All expenses recorded in this group
    expenses: Mapped[list["Expense"]] = relationship(   # type: ignore[name-defined]
        "Expense",
        back_populates="group",
        cascade="all, delete-orphan",
        # Deleting a group removes all its expenses and (via cascade) their splits
    )

    @staticmethod
    def generate_invite_code() -> str:
        return secrets.token_urlsafe(6)

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name!r}>"


class GroupMember(Base, TimestampMixin):
    __tablename__ = "group_members"

    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_group_members_user_group"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[MemberRole] = mapped_column(Enum(MemberRole), nullable=False, default=MemberRole.MEMBER)

    user: Mapped["User"] = relationship("User", back_populates="group_memberships")  # type: ignore[name-defined]
    group: Mapped["Group"] = relationship("Group", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<GroupMember user={self.user_id} group={self.group_id}>"