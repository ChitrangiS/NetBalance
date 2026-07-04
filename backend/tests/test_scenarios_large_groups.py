from decimal import Decimal
import time


def test_twenty_person_group_balances_sum_to_zero(scenario):
    """
    Stress test correctness (not just the pure algorithm from Step 8,
    but the FULL stack: HTTP → service → SQL aggregation → response)
    at a meaningfully larger scale than our usual 3-person fixtures.
    """
    scenario.add_users(20)
    scenario.create_group("user1")
    scenario.join_all_to_group()

    all_keys = [f"user{i}" for i in range(1, 21)]

    # Each of the first 10 people pays for a "round" split among everyone
    for i in range(1, 11):
        scenario.add_expense(
            payer=f"user{i}",
            amount=f"{i * 37.50:.2f}",   # varied, non-round amounts
            split_among=all_keys,
            description=f"Round {i}",
        )

    balances = scenario.get_balances("user1")
    total = sum(Decimal(b["net_balance"]) for b in balances["balances"])
    assert abs(total) < Decimal("0.01")   # conservation law at scale
    assert len(balances["balances"]) == 20   # every member accounted for


def test_twenty_person_settlement_respects_n_minus_1_bound(scenario):
    """
    The formal complexity guarantee from Step 8 — verified end-to-end,
    not just against the pure function — for a 20-person group.
    """
    scenario.add_users(20)
    scenario.create_group("user1")
    scenario.join_all_to_group()

    all_keys = [f"user{i}" for i in range(1, 21)]
    for i in range(1, 8):   # 7 different payers, varied amounts and subsets
        subset = all_keys[:15 + (i % 5)]   # varying participation
        scenario.add_expense(
            payer=f"user{i}",
            amount=f"{(i + 1) * 123.45:.2f}",
            split_among=subset,
            description=f"Expense {i}",
        )

    settlement = scenario.get_settlement("user1")
    assert settlement["transaction_count"] <= 19   # N=20 → max N-1=19


def test_large_group_expense_list_performance_is_reasonable(scenario):
    """
    Not a rigorous load test (that belongs in a separate tool), but a
    basic sanity check: creating and listing many expenses in a
    larger group should complete quickly, indicating no accidental
    N+1 query patterns or quadratic blowups crept in.
    """
    scenario.add_users(15)
    scenario.create_group("user1")
    scenario.join_all_to_group()
    all_keys = [f"user{i}" for i in range(1, 16)]

    start = time.monotonic()
    for i in range(30):   # 30 expenses across a 15-person group
        scenario.add_expense(
            payer=f"user{(i % 15) + 1}",
            amount=f"{50 + i:.2f}",
            split_among=all_keys,
            description=f"Expense {i}",
        )
    balances = scenario.get_balances("user1")
    settlement = scenario.get_settlement("user1")
    elapsed = time.monotonic() - start

    # Generous threshold — this is a correctness/regression guard,
    # not a strict performance benchmark (those need dedicated tooling)
    assert elapsed < 5.0, f"30 expenses + balances + settlement took {elapsed:.2f}s — investigate for N+1 queries"

    total = sum(Decimal(b["net_balance"]) for b in balances["balances"])
    assert abs(total) < Decimal("0.01")
    assert settlement["transaction_count"] <= 14   # N-1 bound for 15 people


def test_fifty_person_group_does_not_crash(scenario):
    """
    Edge of realistic scale — a large company off-site or wedding party.
    The goal here is purely "does the system remain correct and stable",
    not benchmarking — confirms no hardcoded limits or off-by-one
    assumptions break down at this size.
    """
    scenario.add_users(50)
    scenario.create_group("user1")
    scenario.join_all_to_group()
    all_keys = [f"user{i}" for i in range(1, 51)]

    scenario.add_expense(payer="user1", amount="5000.00", split_among=all_keys, description="Big group dinner")
    scenario.add_expense(payer="user25", amount="2500.00", split_among=all_keys, description="Transport")

    balances = scenario.get_balances("user1")
    assert len(balances["balances"]) == 50
    total = sum(Decimal(b["net_balance"]) for b in balances["balances"])
    assert abs(total) < Decimal("0.01")

    settlement = scenario.get_settlement("user1")
    assert settlement["transaction_count"] <= 49