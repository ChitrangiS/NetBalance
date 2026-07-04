from decimal import Decimal
import pytest
from app.services.settlement_service import _greedy_settle


# ═══════════════════════════════════════════════════════════════════════════
# PURE ALGORITHM TESTS — no DB, no HTTP — fast and exhaustive
# ═══════════════════════════════════════════════════════════════════════════

def test_simple_two_person_settlement():
    """Alice +300, Bob -300 → one transaction, Bob pays Alice 300."""
    balances = {1: Decimal("300.00"), 2: Decimal("-300.00")}
    transactions = _greedy_settle(balances)

    assert len(transactions) == 1
    assert transactions[0].from_id == 2
    assert transactions[0].to_id == 1
    assert transactions[0].amount == Decimal("300.00")


def test_already_settled_zero_balances():
    """Everyone at zero → no transactions needed."""
    balances = {1: Decimal("0.00"), 2: Decimal("0.00"), 3: Decimal("0.00")}
    transactions = _greedy_settle(balances)
    assert transactions == []


def test_one_payer_for_everything():
    """Alice +600, Bob -200, Carol -400 — from the theory walkthrough."""
    balances = {
        1: Decimal("600.00"),   # Alice
        2: Decimal("-200.00"),  # Bob
        3: Decimal("-400.00"),  # Carol
    }
    transactions = _greedy_settle(balances)

    assert len(transactions) == 2
    # Largest debtor (Carol, -400) settles with largest creditor (Alice) first
    assert transactions[0].from_id == 3
    assert transactions[0].to_id == 1
    assert transactions[0].amount == Decimal("400.00")

    assert transactions[1].from_id == 2
    assert transactions[1].to_id == 1
    assert transactions[1].amount == Decimal("200.00")


def test_four_person_dry_run_from_theory():
    """Reproduces the exact 4-person dry run from the theory section."""
    balances = {
        1: Decimal("500.00"),    # Alice
        2: Decimal("100.00"),    # Bob
        3: Decimal("-300.00"),   # Carol
        4: Decimal("-300.00"),   # Dave
    }
    transactions = _greedy_settle(balances)

    assert len(transactions) == 3

    # Verify by reconstructing each person's net flow from transactions,
    # rather than asserting exact ordering (which is an implementation detail)
    received = {}
    paid = {}
    for t in transactions:
        paid[t.from_id] = paid.get(t.from_id, Decimal("0")) + t.amount
        received[t.to_id] = received.get(t.to_id, Decimal("0")) + t.amount

    assert received.get(1, Decimal("0")) == Decimal("500.00")   # Alice received 500
    assert received.get(2, Decimal("0")) == Decimal("100.00")   # Bob received 100
    assert paid.get(3, Decimal("0")) == Decimal("300.00")       # Carol paid 300
    assert paid.get(4, Decimal("0")) == Decimal("300.00")       # Dave paid 300


def test_circular_debts_cancel_out_completely():
    """
    Alice owes Bob 100, Bob owes Carol 100, Carol owes Alice 100
    — a perfect cycle. Net balances are all zero. No transactions needed.
    """
    balances = {1: Decimal("0.00"), 2: Decimal("0.00"), 3: Decimal("0.00")}
    transactions = _greedy_settle(balances)
    assert transactions == []


def test_large_group_terminates_within_n_minus_1_transactions():
    """
    Stress test: 20 people with random-ish balances summing to zero.
    The algorithm must terminate, and use at most N-1 = 19 transactions.
    """
    balances = {
        1: Decimal("1000.00"), 2: Decimal("850.00"), 3: Decimal("300.00"),
        4: Decimal("150.00"), 5: Decimal("75.00"),
        6: Decimal("-50.00"), 7: Decimal("-100.00"), 8: Decimal("-150.00"),
        9: Decimal("-200.00"), 10: Decimal("-225.00"), 11: Decimal("-250.00"),
        12: Decimal("-600.00"), 13: Decimal("-100.00"), 14: Decimal("-150.00"),
        15: Decimal("-100.00"), 16: Decimal("-100.00"), 17: Decimal("-50.00"),
        18: Decimal("-100.00"), 19: Decimal("-100.00"), 20: Decimal("-100.00"),
    }
    assert sum(balances.values()) == Decimal("0.00")   # sanity check on test data itself

    transactions = _greedy_settle(balances)
    assert len(transactions) <= 19   # at most N-1


def test_settlement_reconstructs_original_balances_exactly():
    """
    PROPERTY TEST: for any settlement plan, replaying all transactions
    must reconstruct each person's exact original net balance.
    This is the single most important correctness property.
    """
    balances = {
        1: Decimal("733.33"), 2: Decimal("-233.33"),
        3: Decimal("-300.00"), 4: Decimal("-200.00"),
    }
    transactions = _greedy_settle(balances)

    reconstructed = {uid: Decimal("0.00") for uid in balances}
    for t in transactions:
        reconstructed[t.from_id] -= t.amount   # paying reduces your position further negative... 
        reconstructed[t.to_id] += t.amount     # ...wait — let's verify the SIGN convention below

    # A debtor's "payment made" should INCREASE their balance toward zero,
    # and a creditor's "payment received" should DECREASE their balance toward zero.
    # So actually: paying reduces what you owe (moves balance UP toward 0),
    # receiving reduces what you're owed (moves balance DOWN toward 0).
    reconstructed = {uid: Decimal("0.00") for uid in balances}
    for t in transactions:
        reconstructed[t.from_id] += t.amount   # debtor's balance increases (less negative)
        reconstructed[t.to_id] -= t.amount     # creditor's balance decreases (less positive)

    for user_id, original_balance in balances.items():
        # reconstructed[user_id] should equal -original_balance
        # (the transactions FULLY CANCEL the original balance)
        assert reconstructed[user_id] == -original_balance, (
            f"User {user_id}: expected cancellation of {original_balance}, "
            f"got {reconstructed[user_id]}"
        )


def test_dust_threshold_ignores_sub_paisa_balances():
    """
    Balances within the dust threshold (e.g. a stray 0.005 from a
    hypothetical edge case) are treated as already settled.
    """
    balances = {1: Decimal("0.005"), 2: Decimal("-0.005")}
    transactions = _greedy_settle(balances)
    assert transactions == []


def test_single_person_group_no_transactions():
    """A lone group member — trivially balance must be 0, no transactions."""
    balances = {1: Decimal("0.00")}
    transactions = _greedy_settle(balances)
    assert transactions == []


def test_unequal_split_subgroup_settlement():
    """
    A scenario where only some people have non-zero balances —
    settled members shouldn't appear in the transaction list at all.
    """
    balances = {
        1: Decimal("100.00"),   # Alice — owed
        2: Decimal("-100.00"),  # Bob — owes
        3: Decimal("0.00"),     # Carol — already settled, sat out all expenses
    }
    transactions = _greedy_settle(balances)

    assert len(transactions) == 1
    assert transactions[0].from_id == 2
    assert transactions[0].to_id == 1
    involved_users = {transactions[0].from_id, transactions[0].to_id}
    assert 3 not in involved_users   # Carol never appears


# ═══════════════════════════════════════════════════════════════════════════
# API ENDPOINT TESTS — through HTTP, using real expenses
# ═══════════════════════════════════════════════════════════════════════════

def get_user_id(client, token):
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    return r.json()["id"]


def create_expense(client, group_id, token, description, amount, split_with):
    r = client.post(
        f"/groups/{group_id}/expenses/",
        json={"description": description, "amount": amount, "split_type": "equal", "split_with": split_with},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()


def test_settlement_endpoint_classic_scenario(
    client, group_with_members, alice_token, bob_token, carol_token,
):
    """End-to-end: real expenses → real balances → real settlement plan."""
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)
    everyone = [alice_id, bob_id, carol_id]

    create_expense(client, group_id, alice_token, "Dinner", "900.00", everyone)
    create_expense(client, group_id, bob_token, "Cab", "600.00", everyone)
    create_expense(client, group_id, carol_token, "Snacks", "300.00", everyone)
    # Expected balances: Alice +300, Bob 0, Carol -300

    response = client.get(
        f"/groups/{group_id}/settlements/",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["transaction_count"] == 1
    assert data["is_already_settled"] is False
    txn = data["transactions"][0]
    assert txn["from_user_id"] == carol_id
    assert txn["to_user_id"] == alice_id
    assert Decimal(txn["amount"]) == Decimal("300.00")


def test_settlement_endpoint_already_settled(
    client, group_with_members, alice_token,
):
    """No expenses at all → already settled, empty transaction list."""
    group_id = group_with_members["id"]

    response = client.get(
        f"/groups/{group_id}/settlements/",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_count"] == 0
    assert data["is_already_settled"] is True
    assert data["transactions"] == []


def test_settlement_endpoint_non_member_forbidden(client, alice_group, bob_token):
    response = client.get(
        f"/groups/{alice_group['id']}/settlements/",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 403


def test_settlement_plan_never_exceeds_n_minus_1_real_scenario(
    client, group_with_members, alice_token, bob_token, carol_token,
):
    """With 3 group members, settlement should never need more than 2 transactions."""
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)
    everyone = [alice_id, bob_id, carol_id]

    # Lots of expenses, varied payers and amounts
    create_expense(client, group_id, alice_token, "E1", "733.33", everyone)
    create_expense(client, group_id, bob_token, "E2", "150.00", [alice_id, bob_id])
    create_expense(client, group_id, carol_token, "E3", "275.50", everyone)
    create_expense(client, group_id, alice_token, "E4", "60.00", [bob_id, carol_id])

    response = client.get(
        f"/groups/{group_id}/settlements/",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    data = response.json()
    assert data["transaction_count"] <= 2   # N=3 people → max N-1=2 transactions