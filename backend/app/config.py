from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    polygon_api_key: str
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    database_path: str = "/data/portfolio.db"
    data_dir: str = "/data"
    log_level: str = "INFO"
    environment: str = "development"

    # OCI
    oci_bucket_namespace: str = ""
    oci_bucket_name: str = ""
    oci_region: str = "us-ashburn-1"

    # FRED API
    fred_api_key: str = ""

    # Phase 4: Risk limits
    max_position_size_pct: float = 15.0
    max_sector_exposure_pct: float = 30.0
    max_portfolio_delta: float = 500.0
    max_portfolio_beta: float = 1.5
    max_concentration_pct: float = 40.0
    min_cash_reserve_pct: float = 10.0
    max_leverage: float = 1.0
    kelly_fraction: float = 0.25
    correlation_threshold: float = 0.80

    # Phase 5: Position management
    csp_close_profit_min_pct: float = 50.0
    csp_close_profit_max_pct: float = 75.0
    csp_roll_dte_threshold: int = 21
    csp_roll_delta_threshold: float = 0.30
    leaps_exit_profit_target_pct: float = 100.0
    leaps_loss_exit_pct: float = 50.0
    leaps_trend_failure_threshold: str = "bearish"
    swings_trailing_stop_pct: float = 8.0
    swings_breakdown_stop_pct: float = 12.0
    swings_profit_target_pct: float = 25.0
    pmcc_short_call_dte_threshold: int = 14
    pmcc_short_call_profit_target_pct: float = 50.0
    pmcc_delta_adjust_threshold: float = 0.35

    # Phase 5: Monitoring
    monitoring_lookback_days: int = 30
    alert_threshold_health: int = 70
    uptime_check_interval_seconds: int = 300

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()