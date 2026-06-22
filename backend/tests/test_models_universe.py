import pytest
from pydantic import ValidationError


class TestUniverse:
    def test_universe_entry_validates_ticker(self):
        from app.models.universe import UniverseEntry
        entry = UniverseEntry(ticker="AAPL", active=True)
        assert entry.ticker == "AAPL"
        assert entry.active is True

    def test_universe_entry_rejects_empty_ticker(self):
        from app.models.universe import UniverseEntry
        with pytest.raises(ValidationError):
            UniverseEntry(ticker="", active=True)
