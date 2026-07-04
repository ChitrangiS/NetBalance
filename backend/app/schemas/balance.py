from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class MemberBalance(BaseModel):
    """
    One member's net financial position within a group.

    net_balance > 0  →  this person is owed money
    net_balance < 0  →  this person owes money
    net_balance == 0 →  settled up
    """
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str
    email: str
    total_paid: Decimal
    total_owed: Decimal
    net_balance: Decimal


class GroupBalanceResponse(BaseModel):
    """
    Full balance breakdown for a group.

    balances: per-member net positions
    is_settled: True if every member's net_balance is effectively zero
                (within a 1-paisa tolerance for rounding)
    """
    group_id: int
    balances: list[MemberBalance]
    is_settled: bool