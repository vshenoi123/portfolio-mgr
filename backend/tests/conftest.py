import os

import pytest

os.environ.setdefault("POLYGON_API_KEY", "test_key")
os.environ.setdefault("DATABASE_PATH", "/tmp/test.db")


@pytest.fixture
def test_db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def test_data_dir(tmp_path):
    data_dir = tmp_path / "market_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)


@pytest.fixture(autouse=True)
def _override_data_dir(test_data_dir):
    from app.config import settings
    old_data_dir = settings.data_dir
    settings.data_dir = test_data_dir
    yield
    settings.data_dir = old_data_dir
