from decimal import Decimal


def test_single_payer_for_entire_group_trip(scenario):
    """
    The most common real-world scenario: one person (e.g. who booked
    the trip) fronts every single expense. Verifies balances and
    settlement collapse to the simplest possible case.
    """
    (scenario
        .add_users(5)
        .create_group("user1")
        .join_all_to_group()
        .add_expense(payer="user1", amount="500.00", split_among=["user1","user2","user3","user4","user5"], description="Flights")
        .add_expense(payer="user1", amount="1000.00", split_among=["user1","user2","user3","user4","user5"], description="Hotel")
        .add_expense(payer="user1", amount="250.00", split_among=["user1","user2","user3","user4","user5"], description="Food")
    )
    # Total paid by user1: 1750. Split 5 ways = 350 each.
    # user1: 1750-350=+1400   everyone else: 0-350=-350

    assert scenario.balance_for("user1", "user1") == Decimal("1400.00")
    for k in ["user2", "user3", "user4", "user5"]:
        assert scenario.balance_for("user1", k) == Decimal("-350.00")

    settlement = scenario.get_settlement("user1")
    # 4 debtors, all owing the same amount to the same single creditor
    assert settlement["transaction_count"] == 4
    payer_user_id = scenario.user_ids["user1"]
    for txn in settlement["transactions"]:
        assert txn["to_user_id"] == payer_user_id
        assert Decimal(txn["amount"]) == Decimal("350.00")


def test_single_payer_excludes_self_from_split(scenario):
    """
    Edge case: the payer treats colleagues to lunch and doesn't
    include themselves in the split at all (a gift, not a shared cost).
    """
    (scenario
        .add_user("alice", "Alice")
        .add_user("bob", "Bob")
        .add_user("carol", "Carol")
        .create_group("alice")
        .join_all_to_group()
        .add_expense(payer="alice", amount="200.00", split_among=["bob", "carol"], description="Treat")
    )
    # Alice paid 200, owes nothing (not in split_with) → she's owed the full 200
    # Bob and Carol split 200 → 100 each owed

    assert scenario.balance_for("alice", "alice") == Decimal("200.00")
    assert scenario.balance_for("alice", "bob") == Decimal("-100.00")
    assert scenario.balance_for("alice", "carol") == Decimal("-100.00")

    settlement = scenario.get_settlement("alice")
    assert settlement["transaction_count"] == 2


def test_single_payer_multiple_expenses_different_subsets(scenario):
    """
    One payer, but each expense involves a DIFFERENT subset of the group
    (e.g., paying for some people's drinks but not others' across multiple rounds).
    """
    (scenario
        .add_user("alice", "Alice")
        .add_user("bob", "Bob")
        .add_user("carol", "Carol")
        .add_user("dave", "Dave")
        .create_group("alice")
        .join_all_to_group()
        .add_expense(payer="alice", amount="100.00", split_among=["alice", "bob"], description="Round 1")
        .add_expense(payer="alice", amount="150.00", split_among=["alice", "carol", "dave"], description="Round 2")
    )
    # Round 1: alice & bob each owe 50
    # Round 2: alice, carol, dave each owe 50
    # alice paid: 100+150=250, owes: 50+50=100 → net +150
    # bob: owes 50 → net -50
    # carol: owes 50 → net -50
    # dave: owes 50 → net -50

    assert scenario.balance_for("alice", "alice") == Decimal("150.00")
    assert scenario.balance_for("alice", "bob") == Decimal("-50.00")
    assert scenario.balance_for("alice", "carol") == Decimal("-50.00")
    assert scenario.balance_for("alice", "dave") == Decimal("-50.00")

    balances = scenario.get_balances("alice")
    total = sum(Decimal(b["net_balance"]) for b in balances["balances"])
    assert total == Decimal("0.00")