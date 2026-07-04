from decimal import Decimal
from pydantic import BaseModel


class Transaction(BaseModel):
    """One suggested payment: from_user pays to_user a given amount."""
    from_user_id: int
    from_user_name: str
    to_user_id: int
    to_user_name: str
    amount: Decimal


class SettlementPlanResponse(BaseModel):
    """
    The full minimal settlement plan for a group.

    transaction_count is surfaced explicitly so the frontend can
    show "Settle up in just 2 payments!" as a UX hook.
    """
    group_id: int
    transactions: list[Transaction]
    transaction_count: int
    is_already_settled: bool