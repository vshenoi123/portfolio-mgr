import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestOHLCV:
    def test_valid_ohlcv(self):
        from app.models.market_data import OHLCVBar
        bar = OHLCVBar(
            ticker="AAPL",
            timestamp=datetime.now(timezone.utc),
            open=150.0,
            high=155.0,
            low=149.0,
            close=153.0,
            volume=1000000,
        )
        assert bar.ticker == "AAPL"
        assert bar.close == 153.0

    def test_ohlcv_high_must_be_above_low(self):
        from app.models.market_data import OHLCVBar
        with pytest.raises(ValidationError):
            OHLCVBar(
                ticker="AAPL",
                timestamp=datetime.now(timezone.utc),
                open=150.0,
                high=148.0,
                low=149.0,
                close=153.0,
                volume=1000000,
            )

    def test_ohlcv_negative_volume_rejected(self):
        from app.models.market_data import OHLCVBar
        with pytest.raises(ValidationError):
            OHLCVBar(
                ticker="AAPL",
                timestamp=datetime.now(timezone.utc),
                open=150.0,
                high=155.0,
                low=149.0,
                close=153.0,
                volume=-100,
            )

    def test_ohlcv_negative_price_rejected(self):
        from app.models.market_data import OHLCVBar
        with pytest.raises(ValidationError):
            OHLCVBar(
                ticker="AAPL",
                timestamp=datetime.now(timezone.utc),
                open=-1.0,
                high=155.0,
                low=149.0,
                close=153.0,
                volume=1000,
            )


class TestOptionsContract:
    def test_valid_option(self):
        from app.models.market_data import OptionsContract
        opt = OptionsContract(
            ticker="AAPL",
            expiration=datetime(2026, 7, 17),
            strike=150.0,
            option_type="call",
            bid=5.20,
            ask=5.30,
            implied_vol=0.35,
            delta=0.55,
            gamma=0.02,
            theta=-0.05,
            vega=0.12,
            volume=5000,
            open_interest=10000,
        )
        assert opt.strike == 150.0
        assert opt.option_type == "call"

    def test_option_type_validation(self):
        from app.models.market_data import OptionsContract
        with pytest.raises(ValidationError):
            OptionsContract(
                ticker="AAPL",
                expiration=datetime(2026, 7, 17),
                strike=150.0,
                option_type="invalid",
                bid=5.20,
                ask=5.30,
                implied_vol=0.35,
                delta=0.55,
                gamma=0.02,
                theta=-0.05,
                vega=0.12,
                volume=5000,
                open_interest=10000,
            )
