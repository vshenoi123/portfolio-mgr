import pytest


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data

    def test_health_has_db_check(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "database" in data["checks"]
        assert data["checks"]["database"] in ("connected", "error")