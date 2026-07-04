import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_user_payload() -> dict:
    """Reusable valid registration payload."""
    return {
        "email": "alice@example.com",
        "full_name": "Alice Johnson",
        "password": "securepassword123",
    }


@pytest.fixture
def registered_user(client: TestClient, sample_user_payload: dict) -> dict:
    """Register a user and return the response body."""
    response = client.post("/auth/register", json=sample_user_payload)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_token(client: TestClient, registered_user: dict) -> str:
    """Login and return the JWT token string."""
    response = client.post("/auth/login", json={
        "email": "alice@example.com",
        "password": "securepassword123",
    })
    assert response.status_code == 200
    return response.json()["access_token"]


# ── Registration Tests ────────────────────────────────────────────────────────

def test_register_success(client: TestClient, sample_user_payload: dict):
    """Happy path — valid registration returns user data without password."""
    response = client.post("/auth/register", json=sample_user_payload)

    assert response.status_code == 201
    body = response.json()

    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice Johnson"
    assert "id" in body
    assert "created_at" in body
    # Critical security check — password must never appear in response
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email(
    client: TestClient,
    registered_user: dict,
    sample_user_payload: dict,
):
    """Registering the same email twice returns 409 Conflict."""
    response = client.post("/auth/register", json=sample_user_payload)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


def test_register_invalid_email(client: TestClient):
    """Invalid email format returns 422 Unprocessable Entity."""
    response = client.post("/auth/register", json={
        "email": "not-an-email",
        "full_name": "Bob",
        "password": "password123",
    })
    assert response.status_code == 422


def test_register_short_password(client: TestClient):
    """Password under 8 characters returns 422."""
    response = client.post("/auth/register", json={
        "email": "bob@example.com",
        "full_name": "Bob Smith",
        "password": "short",
    })
    assert response.status_code == 422


def test_register_short_name(client: TestClient):
    """Name under 2 characters returns 422."""
    response = client.post("/auth/register", json={
        "email": "bob@example.com",
        "full_name": "B",
        "password": "password123",
    })
    assert response.status_code == 422


# ── Login Tests ───────────────────────────────────────────────────────────────

def test_login_success(client: TestClient, registered_user: dict):
    """Valid credentials return a JWT token."""
    response = client.post("/auth/login", json={
        "email": "alice@example.com",
        "password": "securepassword123",
    })

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20  # Sanity check — not empty


def test_login_wrong_password(client: TestClient, registered_user: dict):
    """Wrong password returns 401, not 403 or 404."""
    response = client.post("/auth/login", json={
        "email": "alice@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401
    # Error message must NOT reveal whether email exists
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_nonexistent_email(client: TestClient):
    """Unknown email returns 401, same message as wrong password."""
    response = client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "somepassword123",
    })
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


# ── Protected Route Tests ─────────────────────────────────────────────────────

def test_get_me_success(client: TestClient, auth_token: str):
    """Valid token returns current user profile."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert "hashed_password" not in body


def test_get_me_no_token(client: TestClient):
    """Request without token returns 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token(client: TestClient):
    """Tampered token returns 401."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer this.is.not.valid"},
    )
    assert response.status_code == 401


def test_get_me_malformed_header(client: TestClient):
    """Missing 'Bearer' prefix returns 401."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "justthetoken"},
    )
    assert response.status_code == 401