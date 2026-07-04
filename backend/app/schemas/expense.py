from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.expense import SplitType


# ── Split schemas (per-person share within an expense) ────────────────────────

class SplitInput(BaseModel):
    """
    One person's share when creating an expense.

    Used for EXACT and PERCENTAGE splits where the caller
    specifies each person's share explicitly.

    For EQUAL splits, this isn't needed — the service calculates it.
    """
    user_id: int
    amount: Decimal | None = Field(
    default=None,
    ge=0,
    )
    percentage: Decimal | None = Field(
    default=None,
    ge=0,
    le=100,
    )


class SplitResponse(BaseModel):
    """One person's share as returned in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount: Decimal
    percentage: Decimal | None


# ── Expense schemas ───────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    """
    Request body for creating a new expense.

    split_with: list of user_ids who share this expense.
    For EQUAL splits, just provide the user_ids.
    For EXACT/PERCENTAGE splits, provide SplitInput objects.

    The model_validator enforces that EXACT splits sum to amount,
    and PERCENTAGE splits sum to 100%.

    We validate at the schema level (fast, friendly error messages)
    AND at the service level (business logic layer).
    Defense in depth.
    """
    description: str = Field(
        min_length=1,
        max_length=255,
        examples=["Dinner at Taj"],
    )
    amount: Decimal = Field(
        gt=0,
        examples=[Decimal("900.00")],
    )
    split_type: SplitType = SplitType.EQUAL
    notes: str | None = Field(default=None, max_length=1000)

    # For EQUAL: list of user_ids (including payer)
    # For EXACT/PERCENTAGE: handled by splits field below
    split_with: list[int] = Field(
        min_length=1,
        description="User IDs who share this expense (must be group members)",
    )

    # For EXACT or PERCENTAGE splits — overrides split_with
    splits: list[SplitInput] | None = Field(
        default=None,
        description="Explicit split details. Required for EXACT and PERCENTAGE types.",
    )

    @model_validator(mode="after")
    def validate_splits(self) -> "ExpenseCreate":
        """
        Cross-field validation: ensure splits are consistent with split_type.

        model_validator runs AFTER all individual field validators pass.
        'mode=after' means self is already a fully constructed object —
        we can access self.amount, self.split_type, etc.
        """
        if self.split_type == SplitType.EXACT:
            if not self.splits:
                raise ValueError("EXACT splits require explicit split amounts")
            total = sum(s.amount for s in self.splits if s.amount is not None)
            if abs(total - self.amount) > Decimal("0.01"):
                # Allow 1 paisa tolerance for rounding
                raise ValueError(
                    f"Exact split amounts ({total}) must sum to "
                    f"expense total ({self.amount})"
                )

        if self.split_type == SplitType.PERCENTAGE:
            if not self.splits:
                raise ValueError("PERCENTAGE splits require percentages")
            total_pct = sum(
                s.percentage for s in self.splits
                if s.percentage is not None
            )
            if abs(total_pct - Decimal("100")) > Decimal("0.01"):
                raise ValueError(
                    f"Percentages must sum to 100 (got {total_pct})"
                )

        return self


class ExpenseResponse(BaseModel):
    """Full expense details returned in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    paid_by: int
    paid_by_name: str        # Denormalized for convenience — avoids client JOIN
    amount: Decimal
    description: str
    notes: str | None
    split_type: SplitType
    splits: list[SplitResponse]
    created_at: datetime

    @classmethod
    def from_expense(cls, expense: "Expense") -> "ExpenseResponse":  # type: ignore[name-defined]
        return cls(
            id=expense.id,
            group_id=expense.group_id,
            paid_by=expense.paid_by,
            paid_by_name=expense.paid_by_user.full_name,
            amount=expense.amount,
            description=expense.description,
            notes=expense.notes,
            split_type=expense.split_type,
            splits=expense.splits,
            created_at=expense.created_at,
        )


class ExpenseSummary(BaseModel):
    """
    Lightweight expense representation for list views.
    Omits the full splits list to keep list responses compact.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    paid_by: int
    paid_by_name: str
    amount: Decimal
    description: str
    split_type: SplitType
    created_at: datetime

    @classmethod
    def from_expense(cls, expense: "Expense") -> "ExpenseSummary":  # type: ignore[name-defined]
        return cls(
            id=expense.id,
            group_id=expense.group_id,
            paid_by=expense.paid_by,
            paid_by_name=expense.paid_by_user.full_name,
            amount=expense.amount,
            description=expense.description,
            split_type=expense.split_type,
            created_at=expense.created_at,
        )