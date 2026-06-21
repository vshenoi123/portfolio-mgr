import pytest
from pydantic import ValidationError


class TestConfig:
    def test_config_loads_from_env(self, monkeypatch):
        monkeypatch.setenv("POLYGON_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_PATH", "/tmp/test.db")
        from app.config import settings
        assert settings.polygon_api_key == "test_key"
        assert settings.database_path == "/tmp/test.db"

    def test_config_requires_polygon_key(self, monkeypatch):
        monkeypatch.delenv("POLYGON_API_KEY", raising=False)
        with pytest.raises(ValidationError):
            from app.config import Settings
            Settings()

    def test_config_has_default_data_dir(self, monkeypatch):
        monkeypatch.setenv("POLYGON_API_KEY", "test_key")
        from app.config import settings
        assert settings.data_dir is not None
