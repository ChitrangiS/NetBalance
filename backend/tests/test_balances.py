from decimal import Decimal
import pytest
from fastapi.testclient import TestClient


def get_user_id(client: TestClient, token: str) -> int:
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    return r.json()["id"]


def create_expense(client, group_id, token, description, amount, split_with):
    r = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": description,
            "amount": amount,
            "split_type": "equal",
            "split_with": split_with,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.json()
    return r.json()


def get_balances(client, group_id, token):
    r = client.get(
        f"/groups/{group_id}/balances/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    return r.json()


# ── Core scenario from the theory section ──────────────────────────────────────

def test_balances_three_expenses_classic_scenario(
    client: TestClient, group_with_members, alice_token, bob_token, carol_token,
):
    """
    Reproduces the worked example from theory:
    Alice pays 900, Bob pays 600, Carol pays 300 — all split equally.
    Expected: Alice +300, Bob 0, Carol -300.
    """
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)
    everyone = [alice_id, bob_id, carol_id]

    create_expense(client, group_id, alice_token, "Dinner", "900.00", everyone)
    create_expense(client, group_id, bob_token, "Cab", "600.00", everyone)
    create_expense(client, group_id, carol_token, "Snacks", "300.00", everyone)

    data = get_balances(client, group_id, alice_token)
    balances_by_user = {b["user_id"]: b for b in data["balances"]}

    assert Decimal(balances_by_user[alice_id]["net_balance"]) == Decimal("300.00")
    assert Decimal(balances_by_user[bob_id]["net_balance"]) == Decimal("0.00")
    assert Decimal(balances_by_user[carol_id]["net_balance"]) == Decimal("-300.00")


# ── Conservation law — THE most important property test ────────────────────────

def test_balances_always_sum_to_zero(
    client: TestClient, group_with_members, alice_token, bob_token, carol_token,
):
    """
    The conservation law: no matter how many expenses, in whatever amounts,
    paid by whoever, split among whoever — the sum of all net balances
    must equal zero (within rounding tolerance).

    This is the single most valuable test in the whole balance system.
    """
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)
    everyone = [alice_id, bob_id, carol_id]

    create_expense(client, group_id, alice_token, "E1", "1000.00", everyone)  # remainder case
    create_expense(client, group_id, bob_token, "E2", "47.00", [alice_id, bob_id])
    create_expense(client, group_id, carol_token, "E3", "333.33", everyone)
    create_expense(client, group_id, alice_token, "E4", "75.50", [bob_id, carol_id])

    data = get_balances(client, group_id, alice_token)
    total = sum(Decimal(b["net_balance"]) for b in data["balances"])

    assert abs(total) < Decimal("0.01")


# ── Single payer scenario ────────────────────────────────────────────────────────

def test_balances_one_payer_for_everything(
    client: TestClient, group_with_members, alice_token, bob_token, carol_token,
):
    """Alice pays for everything — she should be owed the full amount minus her own share."""
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)
    everyone = [alice_id, bob_id, carol_id]

    create_expense(client, group_id, alice_token, "Trip Fund", "3000.00", everyone)

    data = get_balances(client, group_id, alice_token)
    balances_by_user = {b["user_id"]: b for b in data["balances"]}

    # 3000 / 3 = exactly 1000 each
    assert Decimal(balances_by_user[alice_id]["net_balance"]) == Decimal("2000.00")
    assert Decimal(balances_by_user[bob_id]["net_balance"]) == Decimal("-1000.00")
    assert Decimal(balances_by_user[carol_id]["net_balance"]) == Decimal("-1000.00")


# ── Zero balance scenario ─────────────────────────────────────────────────────────

def test_balances_zero_when_no_expenses(client: TestClient, group_with_members, alice_token, bob_token, carol_token):
    """A group with zero expenses — everyone's balance is exactly 0, and is_settled is True."""
    group_id = group_with_members["id"]

    data = get_balances(client, group_id, alice_token)

    assert data["is_settled"] is True
    for b in data["balances"]:
        assert Decimal(b["net_balance"]) == Decimal("0.00")
        assert Decimal(b["total_paid"]) == Decimal("0.00")
        assert Decimal(b["total_owed"]) == Decimal("0.00")


def test_balances_is_settled_true_when_naturally_even(
    client: TestClient, group_with_members, alice_token, bob_token, carol_token,
):
    """
    Each person pays exactly the group average — everyone should net to zero.
    """
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)
    everyone = [alice_id, bob_id, carol_id]

    # Each pays 300, split equally among all 3 — perfectly symmetric
    create_expense(client, group_id, alice_token, "A", "300.00", everyone)
    create_expense(client, group_id, bob_token, "B", "300.00", everyone)
    create_expense(client, group_id, carol_token, "C", "300.00", everyone)

    data = get_balances(client, group_id, alice_token)
    assert data["is_settled"] is True


# ── Unequal splits scenario ───────────────────────────────────────────────────────

def test_balances_unequal_splits_subset_of_members(
    client: TestClient, group_with_members, alice_token, bob_token, carol_token,
):
    """
    Carol isn't included in an expense at all — her balance for THAT
    expense should contribute zero, but she's still in the group balances list.
    """
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)

    # Only Alice and Bob share this expense — Carol sits this one out
    create_expense(client, group_id, alice_token, "Just us two", "200.00", [alice_id, bob_id])

    data = get_balances(client, group_id, alice_token)
    balances_by_user = {b["user_id"]: b for b in data["balances"]}

    assert Decimal(balances_by_user[alice_id]["net_balance"]) == Decimal("100.00")
    assert Decimal(balances_by_user[bob_id]["net_balance"]) == Decimal("-100.00")
    # Carol still appears, with a clean zero — she's a group member regardless
    assert Decimal(balances_by_user[carol_id]["net_balance"]) == Decimal("0.00")


# ── Large group stress test ───────────────────────────────────────────────────────

def test_balances_with_remainder_rounding_still_sums_to_zero(
    client: TestClient, group_with_members, alice_token, bob_token, carol_token,
):
    """₹100 split 3 ways (the classic 33.33/33.33/33.34 case) — must still sum to zero."""
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)
    everyone = [alice_id, bob_id, carol_id]

    create_expense(client, group_id, alice_token, "Odd split", "100.00", everyone)

    data = get_balances(client, group_id, alice_token)
    total = sum(Decimal(b["net_balance"]) for b in data["balances"])
    assert total == Decimal("0.00")   # exact here — no float drift, by design


# ── Authorization ─────────────────────────────────────────────────────────────────

def test_balances_non_member_forbidden(client: TestClient, alice_group, bob_token):
    response = client.get(
        f"/groups/{alice_group['id']}/balances/",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 403


def test_balances_response_sorted_descending(
    client: TestClient, group_with_members, alice_token, bob_token, carol_token,
):
    """Balances should be sorted by net_balance descending — most-owed first."""
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)
    everyone = [alice_id, bob_id, carol_id]

    create_expense(client, group_id, alice_token, "Big one", "900.00", everyone)

    data = get_balances(client, group_id, alice_token)
    net_values = [Decimal(b["net_balance"]) for b in data["balances"]]

    assert net_values == sorted(net_values, reverse=True)