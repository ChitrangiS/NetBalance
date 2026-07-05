from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, DateTime, func
from app.models.base import Base


class RefreshToken(Base):
    """
    Stores issued refresh tokens, enabling:
    1. Token revocation (mark is_revoked=True, app rejects the token)
    2. Rotation detection (if a revoked token is presented, a reuse
       attack is detected — revoke ALL tokens for that user immediately)
    3. Session tracking (each row represents an active session/device)

    Unlike JWTs (which are stateless and unrevocable until expiry),
    refresh tokens REQUIRE this database row — that's the fundamental
    tradeoff: revocability requires state, stateless means unrevocable.
    """
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="refresh_tokens",
    )