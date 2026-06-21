import pytest


@pytest.fixture
def test_db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def test_data_dir(tmp_path):
    data_dir = tmp_path / "market_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)
