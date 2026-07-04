import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_and_login


# ── Create Group ──────────────────────────────────────────────────────────────

def test_create_group_success(client: TestClient, alice_token: str):
    """Creator becomes admin member automatically."""
    response = client.post(
        "/groups/",
        json={"name": "Trip to Goa", "description": "Annual trip"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 201
    body = response.json()

    assert body["name"] == "Trip to Goa"
    assert body["description"] == "Annual trip"
    assert "invite_code" in body
    assert len(body["invite_code"]) > 0
    assert body["member_count"] == 1

    # Creator is the admin
    members = body["members"]
    assert len(members) == 1
    assert members[0]["email"] == "alice@example.com"
    assert members[0]["role"] == "admin"


def test_create_group_unauthenticated(client: TestClient):
    """No token → 401."""
    response = client.post("/groups/", json={"name": "Test Group"})
    assert response.status_code == 401


def test_create_group_name_too_short(client: TestClient, alice_token: str):
    """Name under 2 chars → 422."""
    response = client.post(
        "/groups/",
        json={"name": "X"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 422


# ── Join Group ────────────────────────────────────────────────────────────────

def test_join_group_success(
    client: TestClient,
    alice_group: dict,
    bob_token: str,
):
    """Bob joins Alice's group via invite code."""
    invite_code = alice_group["invite_code"]

    response = client.post(
        "/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["member_count"] == 2
    emails = [m["email"] for m in body["members"]]
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails


def test_join_group_invalid_code(client: TestClient, bob_token: str):
    """Invalid invite code → 404."""
    response = client.post(
        "/groups/join",
        json={"invite_code": "doesnotexist"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 404


def test_join_group_twice(
    client: TestClient,
    alice_group: dict,
    bob_token: str,
):
    """Joining the same group twice → 409 Conflict."""
    invite_code = alice_group["invite_code"]
    headers = {"Authorization": f"Bearer {bob_token}"}

    # First join
    client.post("/groups/join", json={"invite_code": invite_code}, headers=headers)

    # Second join — should fail
    response = client.post(
        "/groups/join",
        json={"invite_code": invite_code},
        headers=headers,
    )
    assert response.status_code == 409


def test_creator_cannot_join_own_group(
    client: TestClient,
    alice_group: dict,
    alice_token: str,
):
    """Alice is already a member when she creates — joining again → 409."""
    response = client.post(
        "/groups/join",
        json={"invite_code": alice_group["invite_code"]},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 409


# ── List Groups ───────────────────────────────────────────────────────────────

def test_list_groups_shows_only_my_groups(
    client: TestClient,
    alice_token: str,
    bob_token: str,
):
    """Alice only sees her own groups, not Bob's."""
    # Alice creates 2 groups
    client.post("/groups/", json={"name": "Alice Group 1"},
                headers={"Authorization": f"Bearer {alice_token}"})
    client.post("/groups/", json={"name": "Alice Group 2"},
                headers={"Authorization": f"Bearer {alice_token}"})

    # Bob creates 1 group
    client.post("/groups/", json={"name": "Bob Group"},
                headers={"Authorization": f"Bearer {bob_token}"})

    # Alice lists her groups
    response = client.get(
        "/groups/",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 200
    groups = response.json()
    assert len(groups) == 2
    names = [g["name"] for g in groups]
    assert "Alice Group 1" in names
    assert "Alice Group 2" in names
    assert "Bob Group" not in names


# ── Get Group Detail ──────────────────────────────────────────────────────────

def test_get_group_detail_success(
    client: TestClient,
    alice_group: dict,
    alice_token: str,
):
    """Member can fetch full group details."""
    group_id = alice_group["id"]
    response = client.get(
        f"/groups/{group_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == group_id
    assert len(body["members"]) == 1


def test_get_group_non_member_forbidden(
    client: TestClient,
    alice_group: dict,
    bob_token: str,
):
    """Non-member trying to view group → 403."""
    group_id = alice_group["id"]
    response = client.get(
        f"/groups/{group_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 403


def test_get_group_after_joining(
    client: TestClient,
    alice_group: dict,
    bob_token: str,
):
    """Bob can view group details after joining."""
    invite_code = alice_group["invite_code"]
    group_id = alice_group["id"]
    headers = {"Authorization": f"Bearer {bob_token}"}

    client.post("/groups/join", json={"invite_code": invite_code}, headers=headers)

    response = client.get(f"/groups/{group_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["member_count"] == 2