from decimal import Decimal


def test_exact_split_with_very_uneven_amounts(scenario):
    """
    EXACT split where one person's share is dramatically larger —
    e.g., someone ordered an expensive dish, others had something small.
    """
    scenario.add_user("alice", "Alice").add_user("bob", "Bob").add_user("carol", "Carol")
    scenario.create_group("alice")
    scenario.join_all_to_group()

    # Fetch IDs AFTER all users exist — avoids any ordering ambiguity
    alice_id = scenario.user_ids["alice"]
    bob_id = scenario.user_ids["bob"]
    carol_id = scenario.user_ids["carol"]

    scenario.add_expense(
        payer="alice", amount="1000.00",
        split_among=["alice", "bob", "carol"],
        split_type="exact",
        splits=[
            {"user_id": alice_id, "amount": "700.00"},
            {"user_id": bob_id, "amount": "200.00"},
            {"user_id": carol_id, "amount": "100.00"},
        ],
        description="Fancy dinner",
    )

    assert scenario.balance_for("alice", "alice") == Decimal("300.00")
    assert scenario.balance_for("alice", "bob") == Decimal("-200.00")
    assert scenario.balance_for("alice", "carol") == Decimal("-100.00")

def test_percentage_split_rent_scenario(scenario):
    """
    Classic real-world PERCENTAGE use case: rent split by room size,
    not equally — e.g., the master bedroom pays a larger percentage.
    """
    (scenario
        .add_user("alice", "Alice")
        .add_user("bob", "Bob")
        .create_group("alice")
        .join_all_to_group()
    )
    alice_id = scenario.user_ids["alice"]
    bob_id = scenario.user_ids["bob"]

    scenario.add_expense(
        payer="alice", amount="30000.00",
        split_among=["alice", "bob"],
        split_type="percentage",
        splits=[
            {"user_id": alice_id, "percentage": "60"},
            {"user_id": bob_id, "percentage": "40"},
        ],
        description="Monthly Rent",
    )
    # Alice paid 30000, owes 60% = 18000 → net +12000
    # Bob owes 40% = 12000 → net -12000

    assert scenario.balance_for("alice", "alice") == Decimal("12000.00")
    assert scenario.balance_for("alice", "bob") == Decimal("-12000.00")


def test_equal_split_among_strict_subset_of_group(scenario):
    """
    Group of 5, but a specific expense is split only among 2 of them.
    Verifies non-participants are correctly excluded from THAT expense's
    splits while still being valid group members overall.
    """
    (scenario
        .add_users(5)
        .create_group("user1")
        .join_all_to_group()
        .add_expense(payer="user1", amount="60.00", split_among=["user1", "user3"])
    )

    assert scenario.balance_for("user1", "user1") == Decimal("30.00")
    assert scenario.balance_for("user1", "user3") == Decimal("-30.00")
    # user2, user4, user5 were never in this split — still zero
    assert scenario.balance_for("user1", "user2") == Decimal("0.00")
    assert scenario.balance_for("user1", "user4") == Decimal("0.00")
    assert scenario.balance_for("user1", "user5") == Decimal("0.00")


def test_mixed_split_types_across_multiple_expenses(scenario):
    """
    Realistic scenario: a single group uses EQUAL for some expenses,
    EXACT for others, and PERCENTAGE for a recurring rent line —
    verifies the system correctly aggregates across heterogeneous split types.
    """
    (scenario
        .add_user("alice", "Alice")
        .add_user("bob", "Bob")
        .create_group("alice")
        .join_all_to_group()
    )
    alice_id = scenario.user_ids["alice"]
    bob_id = scenario.user_ids["bob"]

    # EQUAL: groceries split evenly
    scenario.add_expense(payer="alice", amount="200.00", split_among=["alice", "bob"], split_type="equal")
    # EXACT: alice ordered something pricier
    scenario.add_expense(
        payer="bob", amount="150.00", split_among=["alice", "bob"],
        split_type="exact",
        splits=[
            {"user_id": alice_id, "amount": "100.00"},
            {"user_id": bob_id, "amount": "50.00"},
        ],
    )
    # PERCENTAGE: rent, 50/50
    scenario.add_expense(
        payer="alice", amount="1000.00", split_among=["alice", "bob"],
        split_type="percentage",
        splits=[
            {"user_id": alice_id, "percentage": "50"},
            {"user_id": bob_id, "percentage": "50"},
        ],
    )

    # alice paid: 200+1000=1200, owes: 100(eq)+100(exact)+500(pct)=700 → net +500
    # bob paid: 150, owes: 100(eq)+50(exact)+500(pct)=650 → net -500
    assert scenario.balance_for("alice", "alice") == Decimal("500.00")
    assert scenario.balance_for("alice", "bob") == Decimal("-500.00")

    balances = scenario.get_balances("alice")
    total = sum(Decimal(b["net_balance"]) for b in balances["balances"])
    assert total == Decimal("0.00")