from unittest.mock import MagicMock, patch
from datetime import date, timedelta


def _mock_contract(ticker, strike, contract_type, expiration_date):
    c = MagicMock()
    c.ticker = ticker
    c.strike_price = strike
    c.contract_type = contract_type
    c.expiration_date = expiration_date
    return c


def _mock_snapshot(
    iv=0.25,
    delta=-0.30,
    gamma=0.02,
    theta=-0.05,
    vega=0.10,
    bid=2.45,
    ask=2.55,
    midpoint=2.50,
    price=2.50,
    trade_size=10,
    open_interest=1000,
    break_even=147.50,
    underlying_price=150.0,
):
    snap = MagicMock()
    snap.implied_volatility = iv
    snap.break_even_price = break_even
    snap.open_interest = open_interest

    snap.greeks = MagicMock()
    snap.greeks.delta = delta
    snap.greeks.gamma = gamma
    snap.greeks.theta = theta
    snap.greeks.vega = vega

    snap.last_quote = MagicMock()
    snap.last_quote.bid = bid
    snap.last_quote.ask = ask
    snap.last_quote.midpoint = midpoint

    snap.last_trade = MagicMock()
    snap.last_trade.price = price
    snap.last_trade.size = trade_size

    snap.underlying_asset = MagicMock()
    snap.underlying_asset.price = underlying_price

    return snap


class TestFetchOptionChain:
    @patch("app.engines.options.polygon_chain._get_client")
    def test_returns_list_of_dicts(self, mock_get_client):
        from app.engines.options.polygon_chain import fetch_option_chain

        today = date.today()
        exp1 = (today + timedelta(days=25)).isoformat()
        exp2 = (today + timedelta(days=30)).isoformat()

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_options_contracts.return_value = [
            _mock_contract("O:AAPL250718P00150000", 150.0, "put", exp1),
            _mock_contract("O:AAPL250723P00155000", 155.0, "put", exp2),
        ]

        result = fetch_option_chain("AAPL", "put", 20, 45)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["ticker"] == "O:AAPL250718P00150000"
        assert result[0]["strike"] == 150.0
        assert result[0]["type"] == "put"
        assert result[0]["expiration_date"] == exp1
        assert result[0]["dte"] >= 20
        assert result[1]["strike"] == 155.0

    @patch("app.engines.options.polygon_chain._get_client")
    def test_returns_empty_list_on_api_error(self, mock_get_client):
        from app.engines.options.polygon_chain import fetch_option_chain

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_options_contracts.side_effect = Exception("API error")

        result = fetch_option_chain("AAPL", "put", 20, 45)

        assert result == []


class TestFetchChainSnapshot:
    @patch("app.engines.options.polygon_chain._get_client")
    def test_returns_live_data(self, mock_get_client):
        from app.engines.options.polygon_chain import fetch_chain_snapshot

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_snapshot_option.return_value = _mock_snapshot()

        result = fetch_chain_snapshot("AAPL", "O:AAPL250718P00150000")

        assert result is not None
        assert result["iv"] == 0.25
        assert result["delta"] == -0.30
        assert result["gamma"] == 0.02
        assert result["theta"] == -0.05
        assert result["vega"] == 0.10
        assert result["bid"] == 2.45
        assert result["ask"] == 2.55
        assert result["midpoint"] == 2.50
        assert result["last_price"] == 2.50
        assert result["open_interest"] == 1000
        assert result["volume"] == 10
        assert result["break_even"] == 147.50
        assert result["underlying_price"] == 150.0

    @patch("app.engines.options.polygon_chain._get_client")
    def test_returns_none_on_error(self, mock_get_client):
        from app.engines.options.polygon_chain import fetch_chain_snapshot

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_snapshot_option.side_effect = Exception("API error")

        result = fetch_chain_snapshot("AAPL", "O:AAPL250718P00150000")

        assert result is None

    @patch("app.engines.options.polygon_chain._get_client")
    def test_returns_none_when_snapshot_is_none(self, mock_get_client):
        from app.engines.options.polygon_chain import fetch_chain_snapshot

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_snapshot_option.return_value = None

        result = fetch_chain_snapshot("AAPL", "O:AAPL250718P00150000")

        assert result is None


class TestFindNearestContract:
    def test_picks_closest_delta(self):
        from app.engines.options.polygon_chain import find_nearest_contract

        contracts = [
            {"ticker": "A", "delta": -0.15},
            {"ticker": "B", "delta": -0.32},
            {"ticker": "C", "delta": -0.50},
        ]

        result = find_nearest_contract(contracts, 0.30)

        assert result["ticker"] == "B"
        assert result["delta"] == -0.32

    def test_returns_none_when_no_valid_contracts(self):
        from app.engines.options.polygon_chain import find_nearest_contract

        contracts = [
            {"ticker": "A", "delta": None},
            {"ticker": "B", "delta": None},
        ]

        result = find_nearest_contract(contracts, 0.30)

        assert result is None

    def test_returns_none_on_empty_list(self):
        from app.engines.options.polygon_chain import find_nearest_contract

        result = find_nearest_contract([], 0.30)

        assert result is None

    def test_handles_positive_deltas(self):
        from app.engines.options.polygon_chain import find_nearest_contract

        contracts = [
            {"ticker": "A", "delta": 0.25},
            {"ticker": "B", "delta": 0.35},
            {"ticker": "C", "delta": 0.75},
        ]

        result = find_nearest_contract(contracts, 0.30)

        assert result["ticker"] == "A"
        assert result["delta"] == 0.25


class TestFetchChainWithSnapshots:
    @patch("app.engines.options.polygon_chain.fetch_chain_snapshot")
    @patch("app.engines.options.polygon_chain.fetch_option_chain")
    def test_combines_contracts_with_snapshots(self, mock_fetch_chain, mock_fetch_snap):
        from app.engines.options.polygon_chain import fetch_chain_with_snapshots

        mock_fetch_chain.return_value = [
            {
                "ticker": "O:AAPL250718P00150000",
                "strike": 150.0,
                "type": "put",
                "expiration_date": "2025-07-18",
                "dte": 25,
            },
            {
                "ticker": "O:AAPL250723P00155000",
                "strike": 155.0,
                "type": "put",
                "expiration_date": "2025-07-23",
                "dte": 30,
            },
        ]
        mock_fetch_snap.side_effect = [
            {"iv": 0.25, "delta": -0.30, "bid": 2.45, "ask": 2.55},
            {"iv": 0.28, "delta": -0.35, "bid": 3.10, "ask": 3.20},
        ]

        result = fetch_chain_with_snapshots("AAPL", "put", 20, 45)

        assert len(result) == 2
        assert result[0]["iv"] == 0.25
        assert result[0]["bid"] == 2.45
        assert result[1]["iv"] == 0.28
        assert result[1]["strike"] == 155.0

    @patch("app.engines.options.polygon_chain.fetch_chain_snapshot")
    @patch("app.engines.options.polygon_chain.fetch_option_chain")
    def test_returns_empty_when_no_contracts(self, mock_fetch_chain, mock_fetch_snap):
        from app.engines.options.polygon_chain import fetch_chain_with_snapshots

        mock_fetch_chain.return_value = []

        result = fetch_chain_with_snapshots("AAPL", "put", 20, 45)

        assert result == []
        mock_fetch_snap.assert_not_called()

    @patch("app.engines.options.polygon_chain.fetch_chain_snapshot")
    @patch("app.engines.options.polygon_chain.fetch_option_chain")
    def test_handles_snapshot_failure_gracefully(
        self, mock_fetch_chain, mock_fetch_snap
    ):
        from app.engines.options.polygon_chain import fetch_chain_with_snapshots

        mock_fetch_chain.return_value = [
            {
                "ticker": "O:AAPL250718P00150000",
                "strike": 150.0,
                "type": "put",
                "expiration_date": "2025-07-18",
                "dte": 25,
            },
        ]
        mock_fetch_snap.return_value = None

        result = fetch_chain_with_snapshots("AAPL", "put", 20, 45)

        assert len(result) == 1
        assert result[0]["iv"] is None
        assert result[0]["bid"] is None
        assert result[0]["ask"] is None
