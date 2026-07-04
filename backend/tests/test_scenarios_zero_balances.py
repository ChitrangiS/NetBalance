from decimal import Decimal


def test_brand_new_group_has_zero_everything(scenario):
    """A group with no expenses at all — every field should be clean zeros, no crashes."""
    (scenario
        .add_users(3)
        .create_group("user1")
        .join_all_to_group()
    )

    balances = scenario.get_balances("user1")
    assert balances["is_settled"] is True
    assert len(balances["balances"]) == 3
    for b in balances["balances"]:
        assert Decimal(b["net_balance"]) == Decimal("0.00")
        assert Decimal(b["total_paid"]) == Decimal("0.00")
        assert Decimal(b["total_owed"]) == Decimal("0.00")

    settlement = scenario.get_settlement("user1")
    assert settlement["transaction_count"] == 0
    assert settlement["is_already_settled"] is True
    assert settlement["transactions"] == []


def test_group_settles_to_zero_through_symmetric_activity(scenario):
    """
    Not a brand-new group — genuine expense activity that happens to
    net out perfectly. Distinguishes "never used" zero from "actively
    used but balanced" zero — both should report is_settled=True.
    """
    (scenario
        .add_user("alice", "Alice")
        .add_user("bob", "Bob")
        .create_group("alice")
        .join_all_to_group()
        .add_expense(payer="alice", amount="100.00", split_among=["alice", "bob"])
        .add_expense(payer="bob", amount="100.00", split_among=["alice", "bob"])
    )
    # Both pay 100, both owe 50 each from each expense → owe 100 total each → net 0 each

    balances = scenario.get_balances("alice")
    assert balances["is_settled"] is True
    assert scenario.balance_for("alice", "alice") == Decimal("0.00")
    assert scenario.balance_for("alice", "bob") == Decimal("0.00")

    settlement = scenario.get_settlement("alice")
    assert settlement["transaction_count"] == 0


def test_member_who_joins_but_never_participates_has_zero_balance(scenario):
    """
    A member joins the group but is never included in any expense's
    split_with — they should still appear in balances with a clean 0,
    not be missing or cause an error.
    """
    (scenario
        .add_user("alice", "Alice")
        .add_user("bob", "Bob")
        .add_user("carol", "Carol")   # joins but never participates
        .create_group("alice")
        .join_all_to_group()
        .add_expense(payer="alice", amount="200.00", split_among=["alice", "bob"])
    )

    balances = scenario.get_balances("alice")
    assert len(balances["balances"]) == 3   # Carol still appears
    assert scenario.balance_for("alice", "carol") == Decimal("0.00")

    settlement = scenario.get_settlement("alice")
    carol_id = scenario.user_ids["carol"]
    involved_ids = set()
    for txn in settlement["transactions"]:
        involved_ids.add(txn["from_user_id"])
        involved_ids.add(txn["to_user_id"])
    assert carol_id not in involved_ids   # Carol never needs to pay or receive


def test_zero_balance_does_not_crash_settlement_with_one_active_pair(scenario):
    """
    Mixed scenario: most of the group is at zero, but exactly one
    creditor/debtor pair has a real balance. Verifies the algorithm
    doesn't choke when most heap entries would have been empty.
    """
    (scenario
        .add_users(5)
        .create_group("user1")
        .join_all_to_group()
        # Only user1 and user2 have any expense between them
        .add_expense(payer="user1", amount="50.00", split_among=["user1", "user2"])
    )

    settlement = scenario.get_settlement("user1")
    assert settlement["transaction_count"] == 1
    txn = settlement["transactions"][0]
    assert txn["from_user_id"] == scenario.user_ids["user2"]
    assert txn["to_user_id"] == scenario.user_ids["user1"]
    assert Decimal(txn["amount"]) == Decimal("25.00")