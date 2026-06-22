"""Sector mapping for common tickers. Source: GICS sector classification."""
import logging

logger = logging.getLogger(__name__)

# GICS Sector Map - covers top ~500 stocks by market cap
_TICKER_SECTORS = {
    # Technology
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology", "GOOG": "Technology",
    "AMZN": "Technology", "NVDA": "Technology", "META": "Technology", "TSLA": "Technology",
    "AVGO": "Technology", "ORCL": "Technology", "CRM": "Technology", "ADBE": "Technology",
    "AMD": "Technology", "INTC": "Technology", "CSCO": "Technology", "QCOM": "Technology",
    "TXN": "Technology", "IBM": "Technology", "NOW": "Technology", "AMAT": "Technology",
    "MU": "Technology", "INTU": "Technology", "LRCX": "Technology", "KLAC": "Technology",
    "SNPS": "Technology", "CDNS": "Technology", "MRVL": "Technology", "FTNT": "Technology",
    "PANW": "Technology", "CRWD": "Technology", "ZS": "Technology", "TEAM": "Technology",
    "ABNB": "Technology", "DASH": "Technology", "UBER": "Technology", "SQ": "Technology",
    "SHOP": "Technology", "SNAP": "Technology", "RBLX": "Technology", "NET": "Technology",
    "DDOG": "Technology", "MDB": "Technology", "COIN": "Technology", "PLTR": "Technology",
    "ARM": "Technology", "SMCI": "Technology", "DELL": "Technology", "HPE": "Technology",
    "HPQ": "Technology", "LOGI": "Technology", "WDAY": "Technology", "VEEV": "Technology",
    "TTD": "Technology", "PUBM": "Technology", "IONQ": "Technology", "RGTI": "Technology",
    "APP": "Technology", "GRAB": "Technology", "BIDU": "Technology", "JD": "Technology",
    "PDD": "Technology", "BABA": "Technology", "NIO": "Technology", "XPEV": "Technology",
    "LI": "Technology", "TSM": "Technology", "ASML": "Technology", "MRAM": "Technology",

    # Financials
    "JPM": "Financials", "V": "Financials", "MA": "Financials", "BAC": "Financials",
    "WFC": "Financials", "GS": "Financials", "MS": "Financials", "C": "Financials",
    "AXP": "Financials", "BLK": "Financials", "SCHW": "Financials", "CME": "Financials",
    "ICE": "Financials", "CB": "Financials", "MMC": "Financials", "AON": "Financials",
    "PGR": "Financials", "TRV": "Financials", "MET": "Financials", "AIG": "Financials",
    "PRU": "Financials", "ALL": "Financials", "AFL": "Financials", "MET": "Financials",
    "USB": "Financials", "PNC": "Financials", "TFC": "Financials", "COF": "Financials",
    "DFS": "Financials", "SYF": "Financials", "FIS": "Financials", "FISV": "Financials",
    "ADP": "Financials", "PAYX": "Financials", "SPGI": "Financials", "MCO": "Financials",
    "MSCI": "Financials", "CBOE": "Financials", "MKTX": "Financials", "NDAQ": "Financials",
    "TROW": "Financials", "IVZ": "Financials", "AMG": "Financials", "BBY": "Financials",
    "PYPL": "Financials", "COIN": "Financials", "SOFI": "Financials", "HOOD": "Financials",

    # Healthcare
    "UNH": "Healthcare", "JNJ": "Healthcare", "LLY": "Healthcare", "ABBV": "Healthcare",
    "MRK": "Healthcare", "PFE": "Healthcare", "TMO": "Healthcare", "ABT": "Healthcare",
    "DHR": "Healthcare", "BMY": "Healthcare", "AMGN": "Healthcare", "GILD": "Healthcare",
    "MDT": "Healthcare", "ISRG": "Healthcare", "SYK": "Healthcare", "VRTX": "Healthcare",
    "REGN": "Healthcare", "BSX": "Healthcare", "ZTS": "Healthcare", "ELV": "Healthcare",
    "CI": "Healthcare", "HCA": "Healthcare", "MCK": "Healthcare", "CVS": "Healthcare",
    "CI": "Healthcare", "HUM": "Healthcare", "WBA": "Healthcare", "XRAY": "Healthcare",
    "BIIB": "Healthcare", "MRNA": "Healthcare", "SGEN": "Healthcare", "INCY": "Healthcare",
    "ALNY": "Healthcare", "BGNE": "Healthcare", "ILMN": "Healthcare", "DXCM": "Healthcare",
    "HOLX": "Healthcare", "IQV": "Healthcare", "CRL": "Healthcare", "DOCS": "Healthcare",
    "GEHC": "Healthcare", "ELAN": "Healthcare", "TECH": "Healthcare", "CRGY": "Healthcare",

    # Consumer Discretionary
    "HD": "Consumer Discretionary", "MCD": "Consumer Discretionary", "NKE": "Consumer Discretionary",
    "SBUX": "Consumer Discretionary", "TGT": "Consumer Discretionary", "LOW": "Consumer Discretionary",
    "TJX": "Consumer Discretionary", "ROST": "Consumer Discretionary", "DG": "Consumer Discretionary",
    "DLTR": "Consumer Discretionary", "CMG": "Consumer Discretionary", "YUM": "Consumer Discretionary",
    "MAR": "Consumer Discretionary", "HLT": "Consumer Discretionary", "MGM": "Consumer Discretionary",
    "LVS": "Consumer Discretionary", "WYNN": "Consumer Discretionary", "CZR": "Consumer Discretionary",
    "BKNG": "Consumer Discretionary", "ABNB": "Consumer Discretionary", "EXPE": "Consumer Discretionary",
    "ORLY": "Consumer Discretionary", "AZO": "Consumer Discretionary", "GM": "Consumer Discretionary",
    "F": "Consumer Discretionary", "RIVN": "Consumer Discretionary", "LCID": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary", "EBAY": "Consumer Discretionary", "ETSY": "Consumer Discretionary",
    "CHWY": "Consumer Discretionary", "BBWI": "Consumer Discretionary", "BURL": "Consumer Discretionary",
    "GPS": "Consumer Discretionary", "ANF": "Consumer Discretionary", "AEO": "Consumer Discretionary",

    # Consumer Staples
    "PG": "Consumer Staples", "KO": "Consumer Staples", "PEP": "Consumer Staples",
    "COST": "Consumer Staples", "WMT": "Consumer Staples", "PM": "Consumer Staples",
    "MO": "Consumer Staples", "MDLZ": "Consumer Staples", "CL": "Consumer Staples",
    "KMB": "Consumer Staples", "GIS": "Consumer Staples", "HSY": "Consumer Staples",
    "KHC": "Consumer Staples", "SYY": "Consumer Staples", "ADM": "Consumer Staples",
    "CAG": "Consumer Staples", "SJM": "Consumer Staples", "CPB": "Consumer Staples",
    "KO": "Consumer Staples", "STZ": "Consumer Staples", "DEO": "Consumer Staples",
    "BUD": "Consumer Staples", "MNST": "Consumer Staples", "KDP": "Consumer Staples",
    "KMB": "Consumer Staples", "CLX": "Consumer Staples", "CHD": "Consumer Staples",
    "EL": "Consumer Staples", "CLX": "Consumer Staples", "TSN": "Consumer Staples",
    "HRL": "Consumer Staples", "CAG": "Consumer Staples", "FLO": "Consumer Staples",

    # Industrials
    "CAT": "Industrials", "UNP": "Industrials", "BA": "Industrials", "HON": "Industrials",
    "RTX": "Industrials", "DE": "Industrials", "LMT": "Industrials", "GE": "Industrials",
    "UPS": "Industrials", "WM": "Industrials", "EMR": "Industrials", "ETN": "Industrials",
    "ITW": "Industrials", "GD": "Industrials", "NSC": "Industrials", "CSX": "Industrials",
    "FDX": "Industrials", "DAL": "Industrials", "UAL": "Industrials", "AAL": "Industrials",
    "LUV": "Industrials", "JBLU": "Industrials", "ALK": "Industrials",
    "NOC": "Industrials", "TDG": "Industrials", "CTAS": "Industrials", "GWW": "Industrials",
    "FAST": "Industrials", "PCAR": "Industrials", "WAB": "Industrials", "URI": "Industrials",
    "XYL": "Industrials", "ROK": "Industrials", "ITW": "Industrials", "PH": "Industrials",
    "CARR": "Industrials", "OTIS": "Industrials", "WM": "Industrials", "RSG": "Industrials",

    # Energy
    "XLE": "Energy", "CVX": "Energy", "COP": "Energy", "EOG": "Energy",
    "SLB": "Energy", "MPC": "Energy", "PSX": "Energy", "VLO": "Energy",
    "PXD": "Energy", "OXY": "Energy", "HES": "Energy", "DVN": "Energy",
    "FANG": "Energy", "HAL": "Energy", "BKR": "Energy", "OKE": "Energy",
    "WMB": "Energy", "KMI": "Energy", "EPD": "Energy", "ET": "Energy",
    "MRO": "Energy", "APA": "Energy", "OVV": "Energy", "CTRA": "Energy",
    "AR": "Energy", "SM": "Energy", "MTDR": "Energy", "CPE": "Energy",
    "PARR": "Energy", "FPD": "Energy", "NOG": "Energy", "REI": "Energy",

    # Utilities
    "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities", "D": "Utilities",
    "SRE": "Utilities", "AEP": "Utilities", "EXC": "Utilities", "XEL": "Utilities",
    "ED": "Utilities", "WEC": "Utilities", "ES": "Utilities", "AWK": "Utilities",
    "PCG": "Utilities", "DTE": "Utilities", "ETR": "Utilities", "FE": "Utilities",
    "CEG": "Utilities", "AES": "Utilities", "NRG": "Utilities", "PNW": "Utilities",
    "PPL": "Utilities", "LNT": "Utilities", "CMS": "Utilities", "NU": "Utilities",

    # Materials
    "LIN": "Materials", "APD": "Materials", "SHW": "Materials", "ECL": "Materials",
    "DD": "Materials", "NEM": "Materials", "FCX": "Materials", "NUE": "Materials",
    "VMC": "Materials", "MLM": "Materials", "PPG": "Materials", "ALB": "Materials",
    "CF": "Materials", "MOS": "Materials", "CE": "Materials", "EMN": "Materials",
    "FMC": "Materials", "IFF": "Materials", "RPM": "Materials", "SON": "Materials",
    "AVY": "Materials", "BLL": "Materials", "SEE": "Materials", "WRK": "Materials",

    # Real Estate
    "PLD": "Real Estate", "AMT": "Real Estate", "CCI": "Real Estate", "EQIX": "Real Estate",
    "SPG": "Real Estate", "PSA": "Real Estate", "O": "Real Estate", "WELL": "Real Estate",
    "DLR": "Real Estate", "AVB": "Real Estate", "EQR": "Real Estate", "VTR": "Real Estate",
    "ARE": "Real Estate", "MAA": "Real Estate", "ESS": "Real Estate", "UDR": "Real Estate",
    "EXR": "Real Estate", "CPT": "Real Estate", "INVH": "Real Estate", "AMH": "Real Estate",
    "SUI": "Real Estate", "EQR": "Real Estate", "BXP": "Real Estate", "VNO": "Real Estate",
    "KIM": "Real Estate", "REG": "Real Estate", "HST": "Real Estate", "PEAK": "Real Estate",

    # Communication Services
    "DIS": "Communication Services", "NFLX": "Communication Services", "CMCSA": "Communication Services",
    "T": "Communication Services", "VZ": "Communication Services", "TMUS": "Communication Services",
    "CHTR": "Communication Services", "EA": "Communication Services", "TTWO": "Communication Services",
    "ATVI": "Communication Services", "ROKU": "Communication Services", "PARA": "Communication Services",
    "WBD": "Communication Services", "FOXA": "Communication Services", "FOX": "Communication Services",
    "OMC": "Communication Services", "IPG": "Communication Services", "NWSA": "Communication Services",
    "GOOGL": "Communication Services", "META": "Communication Services", "MTCH": "Communication Services",
    "BILI": "Communication Services", "IQ": "Communication Services", "HUYA": "Communication Services",
    "DOYU": "Communication Services", "WB": "Communication Services", "GRAB": "Communication Services",

    # ETFs
    "SPY": "ETF", "QQQ": "ETF", "IWM": "ETF", "DIA": "ETF",
    "XLF": "ETF", "XLK": "ETF", "XLE": "ETF", "XLV": "ETF",
    "XLI": "ETF", "XLP": "ETF", "XLU": "ETF", "XLB": "ETF",
    "XLRE": "ETF", "XLY": "ETF", "ARKK": "ETF", "TLT": "ETF",
    "HYG": "ETF", "GDX": "ETF", "SLV": "ETF", "USO": "ETF",
    "VOO": "ETF", "VTI": "ETF", "VEA": "ETF", "VWO": "ETF",
    "IVV": "ETF", "QQQM": "ETF", "SCHD": "ETF", "VIG": "ETF",
    "JEPI": "ETF", "JEPQ": "ETF", "DIVO": "ETF", "NUSI": "ETF",
    "XBI": "ETF", "IBB": "ETF", "SMH": "ETF", "SOXX": "ETF",
    "AIQ": "ETF", "BOTZ": "ETF", "ROBO": "ETF", "KWEB": "ETF",
}


def get_sector(ticker: str) -> str:
    """Get sector for a ticker. Returns 'Unknown' if not mapped."""
    return _TICKER_SECTORS.get(ticker.upper(), "Unknown")


def get_all_sectors() -> dict[str, str]:
    """Return the full sector mapping."""
    return dict(_TICKER_SECTORS)
