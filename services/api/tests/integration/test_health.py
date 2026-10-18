import pytest

pytestmark = pytest.mark.db


def test_health_reports_db(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": True}
