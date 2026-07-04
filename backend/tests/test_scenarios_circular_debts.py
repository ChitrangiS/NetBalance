from decimal import Decimal


def test_perfect_three_way_cycle_nets_to_zero(scenario):
    """
    Alice pays for round 1, Bob pays for round 2, Carol pays for round 3 —
    same amount, same 3-way split each time. This is the textbook circular
    debt scenario: A owes B owes C owes A, all equal amounts.

    Net effect: everyone's balance should be EXACTLY zero, and the
    settlement plan should be empty — no transactions needed at all.
    """
    (scenario
        .add_user("alice", "Alice")
        .add_user("bob", "Bob")
        .add_user("carol", "Carol")
        .create_group("alice")
        .join_all_to_group()
        .add_expense(payer="alice", amount="300.00", split_among=["alice", "bob", "carol"], description="Round 1")
        .add_expense(payer="bob", amount="300.00", split_among=["alice", "bob", "carol"], description="Round 2")
        .add_expense(payer="carol", amount="300.00", split_among=["alice", "bob", "carol"], description="Round 3")
    )

    balances = scenario.get_balances("alice")
    for b in balances["balances"]:
        assert Decimal(b["net_balance"]) == Decimal("0.00")
    assert balances["is_settled"] is True

    settlement = scenario.get_settlement("alice")
    assert settlement["transaction_count"] == 0
    assert settlement["is_already_settled"] is True


def test_four_way_cycle_with_uneven_amounts_still_resolves_correctly(scenario):
    """
    A more complex cycle: 4 people, each paying a DIFFERENT amount,
    but the group as a whole still resolves to a consistent, correct
    (non-zero, but minimal) settlement.
    """
    (scenario
        .add_users(4)   # user1, user2, user3, user4
        .create_group("user1")
        .join_all_to_group()
        .add_expense(payer="user1", amount="400.00", split_among=["user1", "user2", "user3", "user4"])
        .add_expense(payer="user2", amount="200.00", split_among=["user1", "user2", "user3", "user4"])
        .add_expense(payer="user3", amount="100.00", split_among=["user1", "user2", "user3", "user4"])
        .add_expense(payer="user4", amount="100.00", split_among=["user1", "user2", "user3", "user4"])
    )
    # Total paid = 800, split 4 ways = 200 each owed
    # user1: 400-200=+200   user2: 200-200=0   user3: 100-200=-100   user4: 100-200=-100

    balances = scenario.get_balances("user1")
    total = sum(Decimal(b["net_balance"]) for b in balances["balances"])
    assert total == Decimal("0.00")   # conservation law holds even with uneven cycle amounts

    assert scenario.balance_for("user1", "user1") == Decimal("200.00")
    assert scenario.balance_for("user1", "user2") == Decimal("0.00")
    assert scenario.balance_for("user1", "user3") == Decimal("-100.00")
    assert scenario.balance_for("user1", "user4") == Decimal("-100.00")

    settlement = scenario.get_settlement("user1")
    assert settlement["transaction_count"] == 2   # 2 debtors → at most 2 transactions


def test_circular_debt_with_partial_cancellation(scenario):
    """
    A cycle that DOESN'T fully cancel — some residual debt remains.
    Verifies the system correctly computes the residual, not a false zero.
    """
    (scenario
        .add_user("alice", "Alice")
        .add_user("bob", "Bob")
        .add_user("carol", "Carol")
        .create_group("alice")
        .join_all_to_group()
        # Alice pays more than her fair share across the cycle
        .add_expense(payer="alice", amount="600.00", split_among=["alice", "bob", "carol"])
        .add_expense(payer="bob", amount="300.00", split_among=["alice", "bob", "carol"])
        .add_expense(payer="carol", amount="300.00", split_among=["alice", "bob", "carol"])
    )
    # Total = 1200, split 3 ways = 400 each
    # Alice: 600-400=+200  Bob: 300-400=-100  Carol: 300-400=-100

    assert scenario.balance_for("alice", "alice") == Decimal("200.00")
    assert scenario.balance_for("alice", "bob") == Decimal("-100.00")
    assert scenario.balance_for("alice", "carol") == Decimal("-100.00")

    settlement = scenario.get_settlement("alice")
    assert settlement["transaction_count"] == 2
    assert settlement["is_already_settled"] is False