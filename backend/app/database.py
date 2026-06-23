import os
import duckdb

_connections: dict[str, duckdb.DuckDBPyConnection] = {}


def get_connection(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    if db_path is None:
        from app.config import settings
        db_path = settings.database_path

    if db_path in _connections:
        conn = _connections[db_path]
        try:
            conn.execute("SELECT 1")
            return conn
        except Exception:
            del _connections[db_path]

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = duckdb.connect(db_path)
    _connections[db_path] = conn
    _init_schema(conn)
    return conn


def close_connection(db_path: str | None = None) -> None:
    if db_path is None:
        from app.config import settings
        db_path = settings.database_path

    conn = _connections.pop(db_path, None)
    if conn:
        conn.close()


def _init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_id START 1;")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            ticker VARCHAR NOT NULL,
            quantity DECIMAL(18,4) NOT NULL DEFAULT 0,
            avg_price DECIMAL(18,4) NOT NULL DEFAULT 0,
            current_price DECIMAL(18,4) NOT NULL DEFAULT 0,
            market_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            cost_basis DECIMAL(18,4) NOT NULL DEFAULT 0,
            unrealized_pl DECIMAL(18,4) NOT NULL DEFAULT 0,
            unrealized_pl_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
            sector VARCHAR NOT NULL DEFAULT 'UNKNOWN',
            beta DECIMAL(10,4) NOT NULL DEFAULT 1.0,
            delta DECIMAL(10,4) NOT NULL DEFAULT 1.0,
            gamma DECIMAL(10,4) NOT NULL DEFAULT 0,
            theta DECIMAL(10,4) NOT NULL DEFAULT 0,
            vega DECIMAL(10,4) NOT NULL DEFAULT 0,
            strategy_type VARCHAR NOT NULL DEFAULT 'equity',
            opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS options_positions (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            ticker VARCHAR NOT NULL,
            option_type VARCHAR NOT NULL,
            strike DECIMAL(18,4) NOT NULL,
            expiration DATE NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            premium_paid DECIMAL(18,4) NOT NULL DEFAULT 0,
            current_premium DECIMAL(18,4) NOT NULL DEFAULT 0,
            market_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            delta DECIMAL(10,4) NOT NULL DEFAULT 0,
            gamma DECIMAL(10,4) NOT NULL DEFAULT 0,
            theta DECIMAL(10,4) NOT NULL DEFAULT 0,
            vega DECIMAL(10,4) NOT NULL DEFAULT 0,
            implied_vol DECIMAL(10,4) NOT NULL DEFAULT 0,
            dte INTEGER NOT NULL DEFAULT 0,
            strategy_type VARCHAR NOT NULL DEFAULT 'csp',
            status VARCHAR NOT NULL DEFAULT 'open',
            opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            date DATE NOT NULL,
            total_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            cash DECIMAL(18,4) NOT NULL DEFAULT 0,
            equity_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            options_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            total_exposure DECIMAL(18,4) NOT NULL DEFAULT 0,
            daily_pl DECIMAL(18,4) NOT NULL DEFAULT 0,
            daily_pl_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
            total_unrealized_pl DECIMAL(18,4) NOT NULL DEFAULT 0,
            max_drawdown DECIMAL(10,4) NOT NULL DEFAULT 0,
            portfolio_beta DECIMAL(10,4) NOT NULL DEFAULT 0,
            portfolio_delta_e DECIMAL(18,4) NOT NULL DEFAULT 0,
            concentration_pct_top5 DECIMAL(10,4) NOT NULL DEFAULT 0,
            sector_exposures VARCHAR DEFAULT '{}',
            correlation_matrix_json VARCHAR DEFAULT '[]',
            portfolio_health_score DECIMAL(10,4) NOT NULL DEFAULT 100,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS capital_allocation (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            date DATE NOT NULL,
            strategy VARCHAR NOT NULL,
            ticker VARCHAR NOT NULL,
            position_size DECIMAL(18,4) NOT NULL DEFAULT 0,
            capital_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
            strategy_allocation_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
            allocation_method VARCHAR NOT NULL DEFAULT 'kelly',
            regime_at_allocation VARCHAR NOT NULL DEFAULT 'Unknown',
            total_portfolio_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            cash_reserve DECIMAL(18,4) NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)


    # Phase 5: Orders and trade journal tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            alpaca_order_id VARCHAR UNIQUE,
            ticker VARCHAR NOT NULL,
            side VARCHAR NOT NULL CHECK(side IN ('buy','sell')),
            order_type VARCHAR NOT NULL CHECK(order_type IN ('market','limit','stop','stop_limit','trailing_stop')),
            time_in_force VARCHAR NOT NULL DEFAULT 'day',
            quantity DECIMAL(18,4) NOT NULL,
            filled_qty DECIMAL(18,4) NOT NULL DEFAULT 0,
            price DECIMAL(18,4),
            stop_price DECIMAL(18,4),
            status VARCHAR NOT NULL DEFAULT 'pending',
            strategy_type VARCHAR NOT NULL DEFAULT 'equity',
            filled_avg_price DECIMAL(18,4),
            filled_at TIMESTAMP WITH TIME ZONE,
            submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            notes VARCHAR DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    # Phase 6: AI reports and self-learning
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            report_date DATE NOT NULL,
            summary VARCHAR,
            sections_json VARCHAR DEFAULT '[]',
            generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS performance_attribution (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            period VARCHAR NOT NULL,
            total_return_pct DECIMAL(10,4) DEFAULT 0,
            best_performer VARCHAR DEFAULT '',
            worst_performer VARCHAR DEFAULT '',
            strategy_breakdown_json VARCHAR DEFAULT '{}',
            sector_breakdown_json VARCHAR DEFAULT '{}',
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS self_learning_signals (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            signal_type VARCHAR NOT NULL,
            ticker VARCHAR NOT NULL,
            predicted_direction VARCHAR,
            actual_outcome VARCHAR,
            accuracy DECIMAL(10,4) DEFAULT 0,
            signal_date DATE NOT NULL,
            resolution_date DATE,
            regime_at_signal VARCHAR DEFAULT 'Unknown',
            notes VARCHAR DEFAULT ''
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            ticker VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            strategy_type VARCHAR NOT NULL,
            entry_price DECIMAL(18,4) NOT NULL,
            exit_price DECIMAL(18,4),
            quantity DECIMAL(18,4) NOT NULL,
            gross_pl DECIMAL(18,4) DEFAULT 0,
            net_pl DECIMAL(18,4) DEFAULT 0,
            commission DECIMAL(18,4) DEFAULT 0,
            entry_date TIMESTAMP WITH TIME ZONE NOT NULL,
            exit_date TIMESTAMP WITH TIME ZONE,
            days_held INTEGER DEFAULT 0,
            exit_reason VARCHAR DEFAULT '',
            regime_at_entry VARCHAR DEFAULT 'Unknown',
            regime_at_exit VARCHAR DEFAULT 'Unknown',
            notes VARCHAR DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

def get_data_dir() -> str:
    from app.config import settings
    return settings.data_dir


def ensure_parquet_dir(ticker: str, data_type: str = "ohlcv") -> str:
    base = get_data_dir()
    path = os.path.join(base, "market_data", data_type, ticker.lower())
    os.makedirs(path, exist_ok=True)
    return path
