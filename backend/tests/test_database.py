from sqlalchemy import text
from sqlalchemy.orm import Session


def test_database_connection(db: Session):
    """
    Verify the test database is reachable and executing queries.
    If this fails, all other DB tests will fail too — catch it early.
    """
    result = db.execute(text("SELECT 1"))
    assert result.scalar() == 1


def test_tables_created(db: Session):
    """
    Verify Base.metadata.create_all() ran successfully.
    No models yet, but the infrastructure should work.
    """
    from sqlalchemy import inspect
    inspector = inspect(db.bind)
    # tables list will grow as we add models in future steps
    tables = inspector.get_table_names()
    # At this point no tables exist — but the DB itself should be accessible
    assert isinstance(tables, list)


def test_health_endpoint(client):
    """API smoke test — verifies the app starts and responds."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"