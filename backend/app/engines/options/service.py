
import numpy as np
from scipy.stats import norm

from app.engines.options.schemas import CSPOption, LEAPSOption, PMMCOption, CoveredCallOption


def black_scholes_d1(
    S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0
) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    return (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))


def black_scholes_d2(
    S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0
) -> float:
    d1 = black_scholes_d1(S, K, T, r, sigma, q)
    return d1 - sigma * np.sqrt(T)


def black_scholes_price(
    S: float, K: float, T: float, r: float, sigma: float,
    option_type: str = "call", q: float = 0.0
) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = black_scholes_d1(S, K, T, r, sigma, q)
    d2 = black_scholes_d2(S, K, T, r, sigma, q)
    if option_type == "call":
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    return float(price)


def black_scholes_delta(
    S: float, K: float, T: float, r: float, sigma: float,
    option_type: str = "call", q: float = 0.0
) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = black_scholes_d1(S, K, T, r, sigma, q)
    if option_type == "call":
        return float(np.exp(-q * T) * norm.cdf(d1))
    else:
        return float(np.exp(-q * T) * (norm.cdf(d1) - 1))


def probability_of_profit(
    S: float, K: float, T: float, r: float, sigma: float,
    option_type: str = "call", premium: float = 0.0
) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    if option_type == "call":
        break_even = K + premium
        d_be = (np.log(S / break_even) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        return float(1.0 - norm.cdf(d_be))
    else:
        break_even = K - premium
        d_be = (np.log(S / break_even) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        return float(norm.cdf(d_be))


def annualized_yield(premium: float, strike: float, days_to_expiration: int) -> float:
    if strike <= 0 or days_to_expiration <= 0:
        return 0.0
    yield_ = (premium / strike) * (365.0 / days_to_expiration)
    return float(yield_)


def _find_strikes_for_delta(
    S: float, sigma: float, T: float, r: float,
    target_delta: float, option_type: str = "put", q: float = 0.0,
    step: float = 2.5
) -> list[dict]:
    strikes = []
    low = max(step, S * 0.5)
    high = S * 1.5
    K = round(low / step) * step
    while K <= high:
        K = round(K / step) * step
        if K <= 0:
            K += step
            continue
        delta = black_scholes_delta(S, K, T, r, sigma, option_type, q)
        price = black_scholes_price(S, K, T, r, sigma, option_type, q)
        strikes.append({"strike": K, "delta": delta, "premium": price})
        K += step
    return strikes


def generate_csp(
    ticker: str, underlying_price: float, implied_volatility: float,
    days_to_expiration: int, target_delta: float = 0.30,
    risk_free_rate: float = 0.05, dividend_yield: float = 0.0,
) -> CSPOption | None:
    T = days_to_expiration / 365.0
    candidates = _find_strikes_for_delta(
        underlying_price, implied_volatility, T, risk_free_rate,
        target_delta, "put", dividend_yield,
    )
    best = min(candidates, key=lambda c: abs(c["delta"] + target_delta))
    K = best["strike"]
    premium = best["premium"]
    delta = best["delta"]
    d1 = black_scholes_d1(underlying_price, K, T, risk_free_rate, implied_volatility, dividend_yield)
    d2 = black_scholes_d2(underlying_price, K, T, risk_free_rate, implied_volatility, dividend_yield)
    gamma = float(norm.pdf(d1) / (underlying_price * implied_volatility * np.sqrt(T))) if T > 0 else 0.0
    theta = float(
        -(underlying_price * norm.pdf(d1) * implied_volatility) / (2 * np.sqrt(T))
        - risk_free_rate * K * np.exp(-risk_free_rate * T) * norm.cdf(-d2)
    ) / 365.0 if T > 0 else 0.0
    vega = float(underlying_price * norm.pdf(d1) * np.sqrt(T) * 0.01)
    rho = float(-K * T * np.exp(-risk_free_rate * T) * norm.cdf(-d2) * 0.01)

    return CSPOption(
        ticker=ticker, strike=K, expiration="",
        premium=round(premium, 2), implied_volatility=implied_volatility,
        delta=round(delta, 4), gamma=round(gamma, 6), theta=round(theta, 6),
        vega=round(vega, 4), rho=round(rho, 4),
        bid=round(premium * 0.95, 2), ask=round(premium * 1.05, 2),
        last_price=round(premium, 2), open_interest=0, volume=0,
        underlying_price=underlying_price, days_to_expiration=days_to_expiration,
        annualized_yield=round(annualized_yield(premium, K, days_to_expiration), 4),
        probability_of_profit=round(
            probability_of_profit(underlying_price, K, T, risk_free_rate, implied_volatility, "put", premium), 4
        ),
    )


def generate_leaps(
    ticker: str, underlying_price: float, implied_volatility: float,
    days_to_expiration: int, target_delta: float = 0.75,
    risk_free_rate: float = 0.05, dividend_yield: float = 0.0,
) -> LEAPSOption | None:
    T = days_to_expiration / 365.0
    candidates = _find_strikes_for_delta(
        underlying_price, implied_volatility, T, risk_free_rate,
        target_delta, "call", dividend_yield,
    )
    best = min(candidates, key=lambda c: abs(c["delta"] - target_delta))
    K = best["strike"]
    premium = best["premium"]
    delta = best["delta"]
    d1 = black_scholes_d1(underlying_price, K, T, risk_free_rate, implied_volatility, dividend_yield)
    d2 = black_scholes_d2(underlying_price, K, T, risk_free_rate, implied_volatility, dividend_yield)
    intrinsic = max(0.0, underlying_price - K)
    time_val = premium - intrinsic
    leverage = (underlying_price / premium) if premium > 0 else 0.0
    gamma = float(norm.pdf(d1) / (underlying_price * implied_volatility * np.sqrt(T))) if T > 0 else 0.0
    theta = float(
        (-(underlying_price * norm.pdf(d1) * implied_volatility) / (2 * np.sqrt(T))
         - risk_free_rate * K * np.exp(-risk_free_rate * T) * norm.cdf(d2)
         + dividend_yield * underlying_price * np.exp(-dividend_yield * T) * norm.cdf(d1))
    ) / 365.0 if T > 0 else 0.0
    vega = float(underlying_price * norm.pdf(d1) * np.sqrt(T) * 0.01)
    rho = float(K * T * np.exp(-risk_free_rate * T) * norm.cdf(d2) * 0.01)

    return LEAPSOption(
        ticker=ticker, strike=K, expiration="",
        premium=round(premium, 2), implied_volatility=implied_volatility,
        delta=round(delta, 4), gamma=round(gamma, 6), theta=round(theta, 6),
        vega=round(vega, 4), rho=round(rho, 4),
        bid=round(premium * 0.95, 2), ask=round(premium * 1.05, 2),
        last_price=round(premium, 2), open_interest=0, volume=0,
        underlying_price=underlying_price, days_to_expiration=days_to_expiration,
        leverage_factor=round(leverage, 2),
        intrinsic_value=round(intrinsic, 2), time_value=round(time_val, 2),
    )


def generate_pmcc(
    ticker: str, underlying_price: float, implied_volatility: float,
    days_to_expiration: int, target_delta: float = 0.75,
    risk_free_rate: float = 0.05, dividend_yield: float = 0.0,
) -> PMMCOption | None:
    T_long = days_to_expiration / 365.0
    T_short = 30.0 / 365.0
    long_candidates = _find_strikes_for_delta(
        underlying_price, implied_volatility, T_long, risk_free_rate,
        target_delta, "call", dividend_yield,
    )
    long_best = min(long_candidates, key=lambda c: abs(c["delta"] - target_delta))
    short_strike = round((long_best["strike"] + 30.0) / 2.5) * 2.5
    short_delta = black_scholes_delta(
        underlying_price, short_strike, T_short, risk_free_rate, implied_volatility, "call", dividend_yield,
    )
    short_premium = black_scholes_price(
        underlying_price, short_strike, T_short, risk_free_rate, implied_volatility, "call", dividend_yield,
    )
    net_debit = long_best["premium"] - short_premium
    max_profit = short_strike - long_best["strike"] - net_debit
    max_loss = net_debit
    break_even = long_best["strike"] + net_debit

    return PMMCOption(
        ticker=ticker, long_strike=long_best["strike"], short_strike=short_strike,
        long_expiration="", short_expiration="",
        long_premium=round(long_best["premium"], 2),
        short_premium=round(short_premium, 2),
        net_debit=round(net_debit, 2), max_profit=round(max_profit, 2),
        max_loss=round(max_loss, 2), break_even=round(break_even, 2),
        delta=round(short_delta, 4), underlying_price=underlying_price,
        days_to_long_expiration=days_to_expiration,
        days_to_short_expiration=30,
        probability_of_profit=round(
            probability_of_profit(underlying_price, break_even, T_short, risk_free_rate, implied_volatility, "call", 0.0), 4
        ),
        annualized_yield=round(
            annualized_yield(net_debit, underlying_price, days_to_expiration), 4
        ),
    )


def generate_covered_call(
    ticker: str, underlying_price: float, implied_volatility: float,
    days_to_expiration: int, target_delta: float = 0.30,
    risk_free_rate: float = 0.05, dividend_yield: float = 0.0,
) -> CoveredCallOption | None:
    T = days_to_expiration / 365.0
    candidates = _find_strikes_for_delta(
        underlying_price, implied_volatility, T, risk_free_rate,
        target_delta, "call", dividend_yield,
    )
    best = min(candidates, key=lambda c: abs(c["delta"] - target_delta))
    K = best["strike"]
    premium = best["premium"]
    delta = best["delta"]
    d1 = black_scholes_d1(underlying_price, K, T, risk_free_rate, implied_volatility, dividend_yield)
    d2 = black_scholes_d2(underlying_price, K, T, risk_free_rate, implied_volatility, dividend_yield)
    gamma = float(norm.pdf(d1) / (underlying_price * implied_volatility * np.sqrt(T))) if T > 0 else 0.0
    theta = float(
        (-(underlying_price * norm.pdf(d1) * implied_volatility) / (2 * np.sqrt(T))
         - risk_free_rate * K * np.exp(-risk_free_rate * T) * norm.cdf(d2)
         + dividend_yield * underlying_price * np.exp(-dividend_yield * T) * norm.cdf(d1))
    ) / 365.0 if T > 0 else 0.0
    vega = float(underlying_price * norm.pdf(d1) * np.sqrt(T) * 0.01)
    rho = float(K * T * np.exp(-risk_free_rate * T) * norm.cdf(d2) * 0.01)

    return CoveredCallOption(
        ticker=ticker, strike=K, expiration="",
        premium=round(premium, 2), implied_volatility=implied_volatility,
        delta=round(delta, 4), gamma=round(gamma, 6), theta=round(theta, 6),
        vega=round(vega, 4), rho=round(rho, 4),
        bid=round(premium * 0.95, 2), ask=round(premium * 1.05, 2),
        last_price=round(premium, 2), open_interest=0, volume=0,
        underlying_price=underlying_price, days_to_expiration=days_to_expiration,
        annualized_yield=round(annualized_yield(premium, underlying_price, days_to_expiration), 4),
        probability_of_profit=round(
            probability_of_profit(underlying_price, K, T, risk_free_rate, implied_volatility, "call", premium), 4
        ),
    )


def generate_csp_live(ticker: str, live: dict) -> CSPOption | None:
    """Generate CSP trade using live Polygon data instead of Black-Scholes."""
    if not live or live.get("strike") is None or live.get("bid") is None:
        return None

    strike = live["strike"]
    underlying = live.get("underlying_price", 0)
    premium = live.get("midpoint") or ((live["bid"] + live["ask"]) / 2)
    T = live.get("dte", 30) / 365.0

    iv = live.get("iv", 0.30)
    r = 0.05
    delta = live.get("delta") or 0
    if delta < 0:
        delta = abs(delta)

    return CSPOption(
        ticker=ticker,
        strike=strike,
        expiration=live.get("expiration_date", ""),
        premium=round(premium, 2),
        implied_volatility=iv,
        delta=round(delta, 4),
        gamma=round(live.get("gamma", 0) or 0, 6),
        theta=round(live.get("theta", 0) or 0, 6),
        vega=round(live.get("vega", 0) or 0, 4),
        rho=0.0,
        bid=round(live["bid"], 2),
        ask=round(live["ask"], 2),
        last_price=round(live.get("last_price", premium) or premium, 2),
        open_interest=live.get("open_interest", 0) or 0,
        volume=live.get("volume", 0) or 0,
        underlying_price=underlying,
        days_to_expiration=live.get("dte", 30),
        annualized_yield=round(annualized_yield(premium, strike, live.get("dte", 30)), 4),
        probability_of_profit=round(
            probability_of_profit(underlying, strike, T, r, iv, "put", premium), 4
        ),
        live_data=True,
    )


def generate_leaps_live(ticker: str, live: dict) -> LEAPSOption | None:
    """Generate LEAPS trade using live Polygon data."""
    if not live or live.get("strike") is None or live.get("bid") is None:
        return None

    strike = live["strike"]
    underlying = live.get("underlying_price", 0)
    premium = live.get("midpoint") or ((live["bid"] + live["ask"]) / 2)
    iv = live.get("iv", 0.30)
    intrinsic = max(0.0, underlying - strike)
    time_val = premium - intrinsic
    leverage = (underlying / premium) if premium > 0 else 0.0

    return LEAPSOption(
        ticker=ticker,
        strike=strike,
        expiration=live.get("expiration_date", ""),
        premium=round(premium, 2),
        implied_volatility=iv,
        delta=round(live.get("delta", 0.70) or 0.70, 4),
        gamma=round(live.get("gamma", 0) or 0, 6),
        theta=round(live.get("theta", 0) or 0, 6),
        vega=round(live.get("vega", 0) or 0, 4),
        rho=0.0,
        bid=round(live["bid"], 2),
        ask=round(live["ask"], 2),
        last_price=round(live.get("last_price", premium) or premium, 2),
        open_interest=live.get("open_interest", 0) or 0,
        volume=live.get("volume", 0) or 0,
        underlying_price=underlying,
        days_to_expiration=live.get("dte", 180),
        leverage_factor=round(leverage, 2),
        intrinsic_value=round(intrinsic, 2),
        time_value=round(time_val, 2),
        live_data=True,
    )


def generate_covered_call_live(ticker: str, live: dict) -> CoveredCallOption | None:
    """Generate Covered Call trade using live Polygon data."""
    if not live or live.get("strike") is None or live.get("bid") is None:
        return None

    strike = live["strike"]
    underlying = live.get("underlying_price", 0)
    premium = live.get("midpoint") or ((live["bid"] + live["ask"]) / 2)
    iv = live.get("iv", 0.30)
    T = live.get("dte", 30) / 365.0

    return CoveredCallOption(
        ticker=ticker,
        strike=strike,
        expiration=live.get("expiration_date", ""),
        premium=round(premium, 2),
        implied_volatility=iv,
        delta=round(abs(live.get("delta", 0.30) or 0.30), 4),
        gamma=round(live.get("gamma", 0) or 0, 6),
        theta=round(live.get("theta", 0) or 0, 6),
        vega=round(live.get("vega", 0) or 0, 4),
        rho=0.0,
        bid=round(live["bid"], 2),
        ask=round(live["ask"], 2),
        last_price=round(live.get("last_price", premium) or premium, 2),
        open_interest=live.get("open_interest", 0) or 0,
        volume=live.get("volume", 0) or 0,
        underlying_price=underlying,
        days_to_expiration=live.get("dte", 30),
        annualized_yield=round(annualized_yield(premium, underlying, live.get("dte", 30)), 4),
        probability_of_profit=round(
            probability_of_profit(underlying, strike, T, 0.05, iv, "call", premium), 4
        ),
        live_data=True,
    )
