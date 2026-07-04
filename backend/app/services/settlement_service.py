import heapq
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.settlement import Transaction, SettlementPlanResponse
from app.services.balance_service import (
    _compute_raw_balances,
    _assert_group_member,
    _get_group_members_with_users,
)

# Balances smaller than this are treated as zero — protects against
# stray sub-paisa artifacts and prevents infinite loops from
# floating-point-style edge cases (even though we use Decimal throughout,
# this is cheap, defensive insurance).
DUST_THRESHOLD = Decimal("0.01")


def calculate_settlement_plan(
    db: Session, group_id: int, current_user: User
) -> SettlementPlanResponse:
    """
    Compute the minimum-transaction settlement plan for a group using
    a greedy "largest creditor meets largest debtor" algorithm.

    This is NOT guaranteed to be the mathematically optimal minimum
    (that's NP-hard to compute exactly) — but it's a fast, well-tested
    approximation that's always within a small constant factor of optimal
    for realistic group sizes, and never exceeds (N-1) transactions.
    """
    _assert_group_member(db, current_user.id, group_id)

    members = _get_group_members_with_users(db, group_id)
    member_by_id = {m.id: m for m in members}

    raw_balances = _compute_raw_balances(db, group_id)

    transactions = _greedy_settle(raw_balances)

    transaction_responses = [
        Transaction(
            from_user_id=t.from_id,
            from_user_name=member_by_id[t.from_id].full_name,
            to_user_id=t.to_id,
            to_user_name=member_by_id[t.to_id].full_name,
            amount=t.amount,
        )
        for t in transactions
    ]

    return SettlementPlanResponse(
        group_id=group_id,
        transactions=transaction_responses,
        transaction_count=len(transaction_responses),
        is_already_settled=len(transaction_responses) == 0,
    )


# ── The core algorithm — pure function, no DB, fully unit-testable ────────────

class _RawTransaction:
    """Internal lightweight transaction record before we attach user names."""
    __slots__ = ("from_id", "to_id", "amount")

    def __init__(self, from_id: int, to_id: int, amount: Decimal):
        self.from_id = from_id
        self.to_id = to_id
        self.amount = amount


def _greedy_settle(balances: dict[int, Decimal]) -> list[_RawTransaction]:
    """
    The greedy minimum-transaction settlement algorithm.

    Input:  {user_id: net_balance}  — must sum to (approximately) zero
    Output: list of transactions that bring every balance to zero

    Implementation uses two max-heaps (via negation, since Python's
    heapq is a min-heap by default):
      - creditors_heap: people who are OWED money (balance > 0)
      - debtors_heap:   people who OWE money (balance < 0)

    At each step, pop the largest creditor and largest debtor,
    settle the smaller of the two magnitudes between them, and
    push back whichever one still has a remaining balance.
    """
    creditors: list[tuple[Decimal, int]] = []   # (-balance, user_id) — negated for max-heap
    debtors: list[tuple[Decimal, int]] = []     # (balance, user_id) — already negative, so min-heap = most negative first

    for user_id, balance in balances.items():
        if balance > DUST_THRESHOLD:
            heapq.heappush(creditors, (-balance, user_id))
        elif balance < -DUST_THRESHOLD:
            heapq.heappush(debtors, (balance, user_id))
        # balances within [-DUST_THRESHOLD, DUST_THRESHOLD] are treated as
        # already settled — no entry needed in either heap

    transactions: list[_RawTransaction] = []

    while creditors and debtors:
        neg_credit_amount, creditor_id = heapq.heappop(creditors)
        credit_amount = -neg_credit_amount    # un-negate

        debt_amount, debtor_id = heapq.heappop(debtors)
        debt_owed = -debt_amount              # debt_amount is negative; flip to positive

        settle_amount = min(credit_amount, debt_owed)
        # Round to 2 decimal places defensively — Decimal min() preserves
        # precision, but we quantize to guarantee currency-clean output
        settle_amount = settle_amount.quantize(Decimal("0.01"))

        transactions.append(_RawTransaction(
            from_id=debtor_id,
            to_id=creditor_id,
            amount=settle_amount,
        ))

        remaining_credit = credit_amount - settle_amount
        remaining_debt = debt_owed - settle_amount

        if remaining_credit > DUST_THRESHOLD:
            heapq.heappush(creditors, (-remaining_credit, creditor_id))

        if remaining_debt > DUST_THRESHOLD:
            heapq.heappush(debtors, (-remaining_debt, debtor_id))

    return transactions