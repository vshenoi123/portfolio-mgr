import pytest
from pydantic import ValidationError


class TestUniverse:
    def test_default_universe_has_spy(self):
        from app.models.universe import DEFAULT_UNIVERSE
        assert "SPY" in DEFAULT_UNIVERSE
        assert "QQQ" in DEFAULT_UNIVERSE

    def test_default_universe_is_list_of_strings(self):
        from app.models.universe import DEFAULT_UNIVERSE
        assert all(isinstance(s, str) for s in DEFAULT_UNIVERSE)
        assert len(DEFAULT_UNIVERSE) > 0

    def test_universe_entry_validates_ticker(self):
        from app.models.universe import UniverseEntry
        entry = UniverseEntry(ticker="AAPL", active=True)
        assert entry.ticker == "AAPL"
        assert entry.active is True

    def test_universe_entry_rejects_empty_ticker(self):
        from app.models.universe import UniverseEntry
        with pytest.raises(ValidationError):
            UniverseEntry(ticker="", active=True)
