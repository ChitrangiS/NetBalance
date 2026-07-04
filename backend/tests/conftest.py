import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.main import app
from app.database import get_db
from app.models import Base
from app.utils.hashing import hash_password
from app.models.user import User
from app.utils.hashing import hash_password
from app.models import Group, GroupMember, MemberRole
from app.models import Expense, ExpenseSplit, SplitType
from decimal import Decimal


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client, email, name):
    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": name,
            "password": "password123",
        },
    )

    assert reg.status_code == 201, reg.text

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "password123",
        },
    )

    assert login.status_code == 200, login.text

    return login.json()["access_token"]

# ── Standard 3-person fixtures (reused from earlier steps) ──────────────────────

@pytest.fixture
def alice_token(client): return register_and_login(client, "alice@example.com", "Alice Johnson")
@pytest.fixture
def bob_token(client):   return register_and_login(client, "bob@example.com", "Bob Smith")
@pytest.fixture
def carol_token(client): return register_and_login(client, "carol@example.com", "Carol White")


@pytest.fixture
def alice_group(client, alice_token):
    r = client.post("/groups/", json={"name": "Trip to Goa"},
                    headers={"Authorization": f"Bearer {alice_token}"})
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def group_with_members(client, alice_token, bob_token, carol_token, alice_group):
    invite = alice_group["invite_code"]
    client.post("/groups/join", json={"invite_code": invite},
                headers={"Authorization": f"Bearer {bob_token}"})
    client.post("/groups/join", json={"invite_code": invite},
                headers={"Authorization": f"Bearer {carol_token}"})
    return alice_group


# ══════════════════════════════════════════════════════════════════════════════
# NEW: Generic scenario builder — supports groups of ANY size, for Step 9 tests
# ══════════════════════════════════════════════════════════════════════════════

class ExpenseScenarioBuilder:
    """
    Test data builder for constructing multi-expense scenarios declaratively.

    Usage:
        scenario = ExpenseScenarioBuilder(client)
        scenario.add_user("alice", "Alice Johnson")
        scenario.add_user("bob", "Bob Smith")
        scenario.create_group("alice", "Trip")
        scenario.join_all_to_group()
        scenario.add_expense(payer="alice", amount="900.00", split_among=["alice", "bob"])
        result = scenario.get_balances("alice")
        plan = scenario.get_settlement("alice")

    This keeps large/complex test scenarios readable as a sequence of
    declarative steps instead of raw repeated HTTP calls.
    """

    def __init__(self, client: TestClient):
        self.client = client
        self.tokens: dict[str, str] = {}      # name -> token
        self.user_ids: dict[str, int] = {}     # name -> user_id
        self.group_id: int | None = None
        self.invite_code: str | None = None

    def add_user(self, key: str, full_name: str) -> "ExpenseScenarioBuilder":
        email = f"{key}@example.com"
        token = register_and_login(self.client, email, full_name)
        self.tokens[key] = token
        r = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.user_ids[key] = r.json()["id"]
        return self

    def add_users(self, count: int, prefix: str = "user") -> "ExpenseScenarioBuilder":
        """Bulk-create N users named user1, user2, ... userN. Useful for large-group tests."""
        for i in range(1, count + 1):
            self.add_user(f"{prefix}{i}", f"User {i}")
        return self

    def create_group(self, creator_key: str, name: str = "Test Group") -> "ExpenseScenarioBuilder":
        r = self.client.post(
            "/groups/",
            json={"name": name},
            headers={"Authorization": f"Bearer {self.tokens[creator_key]}"},
        )
        assert r.status_code == 201, r.json()
        self.group_id = r.json()["id"]
        self.invite_code = r.json()["invite_code"]
        return self

    def join_all_to_group(self, exclude: list[str] | None = None) -> "ExpenseScenarioBuilder":
        """Every registered user except the creator (and any excluded) joins the group."""
        exclude = exclude or []
        for key, token in self.tokens.items():
            r = self.client.post(
                "/groups/join",
                json={"invite_code": self.invite_code},
                headers={"Authorization": f"Bearer {token}"},
            )
            # Creator gets 409 (already a member) — that's expected, not a failure
            if key not in exclude:
                assert r.status_code in (200, 409)
        return self

    def add_expense(
        self,
        payer: str,
        amount: str,
        split_among: list[str],
        description: str = "Test expense",
        split_type: str = "equal",
        splits: list[dict] | None = None,
    ) -> "ExpenseScenarioBuilder":
        user_ids = [self.user_ids[k] for k in split_among]
        body = {
            "description": description,
            "amount": amount,
            "split_type": split_type,
            "split_with": user_ids,
        }
        if splits:
            body["splits"] = splits

        r = self.client.post(
            f"/groups/{self.group_id}/expenses/",
            json=body,
            headers={"Authorization": f"Bearer {self.tokens[payer]}"},
        )
        assert r.status_code == 201, f"Failed to create expense: {r.json()}"
        return self

    def get_balances(self, requester_key: str) -> dict:
        r = self.client.get(
            f"/groups/{self.group_id}/balances/",
            headers={"Authorization": f"Bearer {self.tokens[requester_key]}"},
        )
        assert r.status_code == 200
        return r.json()

    def get_settlement(self, requester_key: str) -> dict:
        r = self.client.get(
            f"/groups/{self.group_id}/settlements/",
            headers={"Authorization": f"Bearer {self.tokens[requester_key]}"},
        )
        assert r.status_code == 200
        return r.json()

    def balance_for(self, requester_key: str, user_key: str) -> Decimal:
        """Convenience: get a specific user's net_balance by their builder key."""
        data = self.get_balances(requester_key)
        target_id = self.user_ids[user_key]
        for b in data["balances"]:
            if b["user_id"] == target_id:
                return Decimal(b["net_balance"])
        raise KeyError(f"User {user_key} not found in balances")
    

@pytest.fixture
def scenario(client) -> ExpenseScenarioBuilder:
    """Provides a fresh ExpenseScenarioBuilder for each test."""
    return ExpenseScenarioBuilder(client)


@pytest.fixture
def db_users(db):
    alice = User(
        email="alice@x.com",
        full_name="Alice",
        hashed_password=hash_password("password123"),
    )
    bob = User(
        email="bob@x.com",
        full_name="Bob",
        hashed_password=hash_password("password123"),
    )
    carol = User(
        email="carol@x.com",
        full_name="Carol",
        hashed_password=hash_password("password123"),
    )

    db.add_all([alice, bob, carol])
    db.commit()

    return {
        "alice": alice,
        "bob": bob,
        "carol": carol,
    }

from app.models import Group, GroupMember, MemberRole

@pytest.fixture
def db_group(db, db_users):
    group = Group(
        name="Trip",
        invite_code="TEST123",
        created_by=db_users["alice"].id,
    )

    db.add(group)
    db.commit()
    db.refresh(group)

    members = [
        GroupMember(
            group_id=group.id,
            user_id=db_users["alice"].id,
            role=MemberRole.ADMIN,
        ),
        GroupMember(
            group_id=group.id,
            user_id=db_users["bob"].id,
            role=MemberRole.MEMBER,
        ),
        GroupMember(
            group_id=group.id,
            user_id=db_users["carol"].id,
            role=MemberRole.MEMBER,
        ),
    ]

    db.add_all(members)
    db.commit()

    return group

@pytest.fixture
def db_expense(db, db_group, db_users):
    expense = Expense(
        group_id=db_group.id,
        paid_by=db_users["alice"].id,
        amount=Decimal("900.00"),
        description="Dinner",
        split_type=SplitType.EQUAL,
    )

    db.add(expense)
    db.commit()
    db.refresh(expense)

    db.add_all([
        ExpenseSplit(
            expense_id=expense.id,
            user_id=db_users["alice"].id,
            amount=Decimal("300.00"),
        ),
        ExpenseSplit(
            expense_id=expense.id,
            user_id=db_users["bob"].id,
            amount=Decimal("300.00"),
        ),
        ExpenseSplit(
            expense_id=expense.id,
            user_id=db_users["carol"].id,
            amount=Decimal("300.00"),
        ),
    ])

    db.commit()
    db.refresh(expense)

    return expense