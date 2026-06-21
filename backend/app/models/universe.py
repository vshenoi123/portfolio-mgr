from pydantic import BaseModel, field_validator


DEFAULT_UNIVERSE = [
    "SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLV",
    "XLI", "XLP", "XLU", "XLB", "XLRE", "XLY",
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "V", "JNJ", "WMT", "MA", "PG", "UNH", "HD", "BAC",
    "DIS", "ADBE", "NFLX", "CRM", "KO", "PEP", "MRK", "ABBV",
    "AVGO", "CSCO", "INTC", "AMD", "QCOM", "TMO", "ACN", "TXN",
    "NKE", "UPS", "BA", "CAT", "GS", "MS", "C", "WFC",
    "ORCL", "IBM", "PYPL", "SNAP", "UBER", "SQ", "SHOP",
    "ARKK", "TLT", "HYG", "GDX", "SLV", "USO",
]


class UniverseEntry(BaseModel):
    ticker: str
    active: bool = True

    @field_validator("ticker")
    @classmethod
    def ticker_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ticker cannot be empty")
        return v.upper().strip()
