from decimal import Decimal
import pytest
from fastapi.testclient import TestClient


def get_user_id(client: TestClient, token: str) -> int:
    """Helper: get a user's own ID via /auth/me."""
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    return r.json()["id"]


# ── Rounding algorithm unit tests (no HTTP, pure function) ────────────────────

def test_equal_split_divides_evenly():
    """₹900 / 3 = exact 300 each — no remainder case."""
    from app.services.expense_service import calculate_equal_splits

    shares = calculate_equal_splits(
        amount=Decimal("900.00"),
        user_ids=[1, 2, 3],
        payer_id=1,
    )
    assert shares == {1: Decimal("300.00"), 2: Decimal("300.00"), 3: Decimal("300.00")}
    assert sum(shares.values()) == Decimal("900.00")


def test_equal_split_with_remainder_sums_exactly():
    """₹1000 / 3 — the classic non-dividing case. Sum MUST equal 1000.00."""
    from app.services.expense_service import calculate_equal_splits

    shares = calculate_equal_splits(
        amount=Decimal("1000.00"),
        user_ids=[1, 2, 3],
        payer_id=1,
    )
    assert sum(shares.values()) == Decimal("1000.00")
    # Payer absorbs the extra cent
    assert shares[1] == Decimal("333.34")
    assert shares[2] == Decimal("333.33")
    assert shares[3] == Decimal("333.33")


def test_equal_split_seven_people():
    """₹100 / 7 — remainder of 4 cents, distributed by payer absorbing all."""
    from app.services.expense_service import calculate_equal_splits

    shares = calculate_equal_splits(
        amount=Decimal("100.00"),
        user_ids=[1, 2, 3, 4, 5, 6, 7],
        payer_id=1,
    )
    assert sum(shares.values()) == Decimal("100.00")
    # base = 14.28, remainder = 0.04 → payer gets 14.28 + 0.04 = 14.32
    assert shares[1] == Decimal("14.32")
    for uid in [2, 3, 4, 5, 6, 7]:
        assert shares[uid] == Decimal("14.28")


def test_equal_split_single_person():
    """Edge case: only one person in the split — they owe the full amount."""
    from app.services.expense_service import calculate_equal_splits

    shares = calculate_equal_splits(
        amount=Decimal("500.00"),
        user_ids=[1],
        payer_id=1,
    )
    assert shares == {1: Decimal("500.00")}


def test_equal_split_zero_people_raises():
    """Edge case: empty user list must raise, not silently produce {}."""
    from app.services.expense_service import calculate_equal_splits

    with pytest.raises(ValueError):
        calculate_equal_splits(amount=Decimal("100.00"), user_ids=[], payer_id=1)


def test_equal_split_large_group_no_drift():
    """₹1.00 split among 100 people — extreme rounding stress test."""
    from app.services.expense_service import calculate_equal_splits

    user_ids = list(range(1, 101))
    shares = calculate_equal_splits(
        amount=Decimal("1.00"),
        user_ids=user_ids,
        payer_id=1,
    )
    assert sum(shares.values()) == Decimal("1.00")


# ── API endpoint tests ──────────────────────────────────────────────────────────

def test_create_expense_equal_split(client: TestClient, group_with_members, alice_token, bob_token, carol_token):
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)

    response = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": "Dinner",
            "amount": "900.00",
            "split_type": "equal",
            "split_with": [alice_id, bob_id, carol_id],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 201
    body = response.json()

    assert body["description"] == "Dinner"
    assert body["amount"] == "900.00"
    assert body["paid_by"] == alice_id
    assert body["paid_by_name"] == "Alice Johnson"
    assert len(body["splits"]) == 3

    total = sum(Decimal(s["amount"]) for s in body["splits"])
    assert total == Decimal("900.00")


def test_create_expense_with_remainder(client: TestClient, group_with_members, alice_token, bob_token, carol_token):
    """₹1000 split 3 ways via the actual API — verify exact sum."""
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)

    response = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": "Groceries",
            "amount": "1000.00",
            "split_type": "equal",
            "split_with": [alice_id, bob_id, carol_id],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    total = sum(Decimal(s["amount"]) for s in body["splits"])
    assert total == Decimal("1000.00")


def test_create_expense_non_member_in_split_with_rejected(
    client: TestClient, alice_group, alice_token, bob_token,
):
    """Bob hasn't joined the group — including him in split_with must fail."""
    group_id = alice_group["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)

    response = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": "Dinner",
            "amount": "500.00",
            "split_type": "equal",
            "split_with": [alice_id, bob_id],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 400
    assert "not members" in response.json()["detail"]


def test_create_expense_non_member_payer_rejected(
    client: TestClient, alice_group, bob_token,
):
    """Bob isn't a member of Alice's group — he can't create expenses there."""
    group_id = alice_group["id"]

    response = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": "Dinner",
            "amount": "500.00",
            "split_type": "equal",
            "split_with": [1],
        },
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 403


def test_create_expense_negative_amount_rejected(
    client: TestClient, alice_group, alice_token,
):
    response = client.post(
        f"/groups/{alice_group['id']}/expenses/",
        json={
            "description": "Bad expense",
            "amount": "-100.00",
            "split_type": "equal",
            "split_with": [1],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 422


def test_create_expense_exact_split(client: TestClient, group_with_members, alice_token, bob_token, carol_token):
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)
    carol_id = get_user_id(client, carol_token)

    response = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": "Custom order",
            "amount": "900.00",
            "split_type": "exact",
            "split_with": [alice_id, bob_id, carol_id],
            "splits": [
                {"user_id": alice_id, "amount": "500.00"},
                {"user_id": bob_id, "amount": "300.00"},
                {"user_id": carol_id, "amount": "100.00"},
            ],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    splits_by_user = {s["user_id"]: Decimal(s["amount"]) for s in body["splits"]}
    assert splits_by_user[alice_id] == Decimal("500.00")
    assert splits_by_user[bob_id] == Decimal("300.00")
    assert splits_by_user[carol_id] == Decimal("100.00")


# ── List / Get tests ─────────────────────────────────────────────────────────

def test_list_expenses(client: TestClient, group_with_members, alice_token):
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)

    for desc in ["Lunch", "Cab"]:
        client.post(
            f"/groups/{group_id}/expenses/",
            json={
                "description": desc, "amount": "100.00",
                "split_type": "equal", "split_with": [alice_id],
            },
            headers={"Authorization": f"Bearer {alice_token}"},
        )

    response = client.get(
        f"/groups/{group_id}/expenses/",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 200
    expenses = response.json()
    assert len(expenses) == 2
    # Newest first
    assert expenses[0]["description"] == "Cab"


def test_list_expenses_non_member_forbidden(client: TestClient, alice_group, bob_token):
    response = client.get(
        f"/groups/{alice_group['id']}/expenses/",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 403


def test_get_expense_detail(client: TestClient, group_with_members, alice_token):
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)

    created = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": "Dinner", "amount": "300.00",
            "split_type": "equal", "split_with": [alice_id],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    ).json()

    response = client.get(
        f"/groups/{group_id}/expenses/{created['id']}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_expense_not_found(client: TestClient, group_with_members, alice_token):
    response = client.get(
        f"/groups/{group_with_members['id']}/expenses/99999",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 404


# ── Delete tests ─────────────────────────────────────────────────────────────

def test_delete_expense_by_payer(client: TestClient, group_with_members, alice_token):
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)

    created = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": "Dinner", "amount": "300.00",
            "split_type": "equal", "split_with": [alice_id],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    ).json()

    response = client.delete(
        f"/groups/{group_id}/expenses/{created['id']}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 204

    # Confirm it's actually gone
    get_response = client.get(
        f"/groups/{group_id}/expenses/{created['id']}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert get_response.status_code == 404


def test_delete_expense_by_non_payer_non_admin_forbidden(
    client: TestClient, group_with_members, alice_token, bob_token, carol_token,
):
    """Carol (regular member) cannot delete Bob's... wait, Alice's expense she didn't pay for."""
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)

    created = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": "Dinner", "amount": "300.00",
            "split_type": "equal", "split_with": [alice_id, bob_id],
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    ).json()

    # Bob didn't pay and isn't admin — should be forbidden
    response = client.delete(
        f"/groups/{group_id}/expenses/{created['id']}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 403


def test_delete_expense_by_admin_who_did_not_pay(
    client: TestClient, group_with_members, alice_token, bob_token,
):
    """Alice is admin — can delete Bob's expense even though she didn't pay."""
    group_id = group_with_members["id"]
    alice_id = get_user_id(client, alice_token)
    bob_id = get_user_id(client, bob_token)

    created = client.post(
        f"/groups/{group_id}/expenses/",
        json={
            "description": "Bob's treat", "amount": "200.00",
            "split_type": "equal", "split_with": [alice_id, bob_id],
        },
        headers={"Authorization": f"Bearer {bob_token}"},
    ).json()

    response = client.delete(
        f"/groups/{group_id}/expenses/{created['id']}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 204