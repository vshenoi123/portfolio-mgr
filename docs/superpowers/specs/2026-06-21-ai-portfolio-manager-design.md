# AI Portfolio Manager & Trading Automation Platform — Design Spec

## Overview

A personal AI hedge-fund style portfolio management platform that discovers trading opportunities, analyzes market regimes, recommends strategies, allocates capital, executes trades, monitors positions, and optimizes risk-adjusted returns.

Target horizon: multi-day to multi-week swing trades, 30-45 DTE cash secured puts, 12-24 month LEAPS, and PMCC/covered call income strategies.

## Architecture

**Approach: Modular Monolith** — Single FastAPI backend with all engines as Python packages, Celery for async background tasks, Next.js frontend, DuckDB + Parquet storage, deployed via Docker Compose on Oracle Cloud Free Tier.

### Container Layout (OCI Free Tier — Ampere A1, 4 OCPU, 24GB RAM)

| Container | RAM | CPU | Role |
|---|---|---|---|
| backend | 2GB | 1.0 | FastAPI + Celery worker (in one process) |
| frontend | 512MB | 0.5 | Next.js standalone |
| redis | 256MB | 0.25 | Cache + Celery broker |
| nginx | 128MB | 0.25 | Reverse proxy |
| **Total** | **~3GB** | **2.0** | 21GB RAM / 2 OCPU headroom |

### Data Flow

Celery Beat scheduler triggers daily pipeline:

1. **Data Engine** → Polygon API → OHLCV + options → Parquet files
2. **Feature Engineering** → Compute indicators → Indicators Parquet
3. **Market Regime** → HMM on SPY → Regime predictions → Regime Parquet
4. **Breakout Detection** → Gaussian channel + volatility compression + market structure → Breakouts Parquet
5. **Opportunity Ranking** → Weighted scoring (25% regime + 20% breakout + 20% RS + 15% CUSUM + 10% volume + 10% trend) + XGBoost refinement → Opportunities Parquet
6. **Portfolio Intelligence** → Load positions from DuckDB → Portfolio impact scoring
7. **Capital Allocation** → Kelly / Risk parity → Position sizing
8. **AI Portfolio Manager** → LLM prompt → Daily report

User executes trades via frontend → POST /api/v1/trading/execute → Risk validation → Alpaca API → Position created in DuckDB.

## Storage

### Parquet Files (write-once, read-many / analytical data)

- `market_data/ohlcv/{ticker}/{year}/{month}.parquet`
- `market_data/options/{ticker}/{date}.parquet`
- `market_data/indicators/{ticker}/{year}/{month}.parquet`
- `signals/regime/{date}.parquet`
- `signals/breakouts/{date}.parquet`
- `signals/opportunities/{date}.parquet`
- `signals/cusum/{date}.parquet`

### DuckDB Native Tables (operational / ACID state)

- `positions` — open equity positions
- `orders` — order history
- `options_positions` — open options strategies
- `portfolio_snapshots` — daily portfolio state
- `capital_allocation` — allocation decisions
- `trade_journal` — closed trades
- `performance_attribution` — strategy-level returns
- `self_learning_signals` — signal efficacy tracking
- `daily_reports` — AI-generated reports

## API Design

All endpoints under `/api/v1/`. Versioned from day 1. Six domains:

| Domain | Key Endpoints |
|---|---|
| Data | GET ohlcv/{ticker}, GET options/{ticker}, POST refresh/{ticker}, POST refresh-all, GET universe |
| Analysis | GET indicators/{ticker}, GET regime, GET regime/{ticker}, GET breakouts, GET breakouts/{ticker}, GET cusum/{ticker} |
| Opportunities | GET opportunities, GET opportunities/{swing,csp,leaps,pmcc}, GET opportunities/{ticker}, GET strategy/{ticker}, GET options/generate/{strategy} |
| Portfolio | GET summary, GET holdings, GET options, GET health, GET exposure, GET impact/{ticker}, GET allocation, POST optimize |
| Trading | POST execute, POST cancel/{id}, POST modify/{id}, GET orders, GET positions, POST close/{id} |
| AI Manager | GET report/daily, GET report/{date}, GET recommendations, POST analyze/{ticker}, GET performance |

## Engine Architecture

Each engine is a Python package under `backend/app/engines/<name>/` containing:

- `__init__.py` — public exports
- `schemas.py` — Pydantic models
- `service.py` — business logic
- `router.py` — FastAPI route definitions (optional, for engines with API endpoints)
- `tasks.py` — Celery task definitions (optional)

This structure allows any engine to be extracted into a standalone microservice later by adding `main.py` with a FastAPI app.

### Engine List

1. **Data Engine** — Polygon API integration, OHLCV + options data collection, universe management
2. **Feature Engineering Engine** — Trend (EMA20/50/200, SMA50/200), momentum (RSI, MACD, ROC, PPO, Stochastic), volatility (ATR, HV, RV, Bollinger width), volume (RelVol, OBV, A/D), market relative (RS vs SPY, RS vs sector)
3. **Market Regime Engine** — HMM (2-6 states), regimes: Bull, Bull High Vol, Bear, Bear High Vol, Range, Crisis. Output: regime + probability + confidence + explanation
4. **Change Point Engine** — CUSUM: return deviations, rolling mean, dynamic threshold. Output: positive/negative shift + change probability + shift date
5. **Breakout Detection Engine** — Gaussian filtered channel (upper/lower bands), volatility compression (BB + KC squeeze), market structure (HH/HL, support/resistance breaks), volume confirmation
6. **Opportunity Ranking Engine** — Weighted composite score, strategy-specific filtering (swing/csp/leaps/pmcc), top-N ranking
7. **Strategy Selection Engine** — Multi-class output (Buy Stock, Buy LEAPS, Sell CSP, PMCC, Covered Call, Close, Roll, Hold, Avoid) + confidence + reasoning + risk assessment
8. **Options Engine** — CSP (strike, expiration, delta, premium, yield, PoP), LEAPS (expiration, strike, delta, cost, breakeven), PMCC (long LEAPS + short call), CC (strike, premium)
9. **Portfolio Intelligence Engine** — Portfolio impact scoring, concentration checks, correlation analysis, portfolio delta/beta, sector exposure adjustment
10. **Capital Allocation Engine** — Position sizing, regime-aware allocation (Bull → more LEAPS/equity, Bear → cash/defensive CSP, Range → income), Kelly / Risk parity
11. **Risk Management Engine** — Max drawdown, exposure limits, concentration limits, correlation limits, volatility limits, trade blocking
12. **Trade Execution Engine** — Alpaca API integration, order placement/cancellation/modification, fill tracking, portfolio sync
13. **Position Management Engine** — CSP (close at 50-75% profit, roll at 21 DTE), LEAPS (profit target, trend failure, regime change), Swing (trailing stop, breakdown, profit target), PMCC (short call roll management)
14. **Opportunity Cost Engine** — Every trade competes with existing holdings, watchlist, cash; generates ranking of best use of next dollar
15. **Trade Replacement Engine** — Evaluates existing positions; recommends keep/reduce/exit/replace based on risk-adjusted scores
16. **Portfolio Monitoring Engine** — Alpaca connection, position/order/cash monitoring, Portfolio Health Score generation
17. **AI Portfolio Manager** — Daily report generation via LLM, market regime summary, portfolio health, opportunities, risks, recommendations, capital allocation, self-learning analysis

## Machine Learning Models

| Model | Library | Purpose | Retrain |
|---|---|---|---|
| HMM (2-6 states) | hmmlearn | Market regime detection | Daily |
| CUSUM detector | custom (numpy) | Change point detection | Real-time |
| XGBoost regressor | xgboost | Opportunity scoring | Weekly |
| LightGBM ranker | lightgbm | Trade ranking (LambdaRank) | Weekly |
| Gaussian filter | scipy | Breakout channel | Real-time |
| LLM (OpenAI/Ollama) | langchain | AI reports + analysis | N/A (prompt) |

## Frontend (Next.js)

### Theme — Terminal Green (matching stock-screener)

- **Colors:** `terminal-green: '#22c55e'`, `terminal-amber: '#ffb700'`, `terminal-red: '#f87171'`, bg-black, zinc-950/900 for surfaces, zinc-800 for borders
- **Fonts:** IBM Plex Mono (data/tables) + IBM Plex Sans (body)
- **Icons:** lucide-react
- **Charts:** lightweight-charts (TradingView) for ticker charts, recharts for portfolio visualizations

### Pages

| Route | Content |
|---|---|
| `/` | Dashboard: RegimeBanner, PortfolioHealthCard, TopOpportunities table, PositionSummary, DailyReportCard |
| `/opportunities` | FilterBar (Swing/CSP/LEAPS/PMCC), sortable OpportunityTable, OpportunityDetail modal with analysis + charts |
| `/portfolio` | AllocationPieChart, ExposureBarChart, HoldingsTable, OptionsTable, PerformanceChart |
| `/positions/[id]` | PositionDetail, OptionsStrategyDisplay, ActionPanel (Close/Roll/Adjust) |
| `/reports` | DailyReportView, PerformanceAttribution, SelfLearningInsights |
| `/settings` | API keys, Trading preferences, Risk limits, Universe management |

### Shared Components

DataTable (sortable/striped/clickable), ScoreBadge (color-coded), RegimeDot, PctChange (green/red), Modal, StrategyCard, ActionButton, StatusDot

## Deployment

### CI/CD (GitHub Actions)

- On push to main: build Docker images, push to OCI Container Registry, SSH into VM, `docker compose pull && docker compose up -d`
- Daily cron: backup Parquet directories to OCI Object Storage

### Project Structure

```
portfolio-mgr/
├── backend/
│   ├── app/
│   │   ├── engines/       # 17 engine packages
│   │   │   ├── data/
│   │   │   ├── features/
│   │   │   ├── regime/
│   │   │   ├── cusum/
│   │   │   ├── breakout/
│   │   │   ├── opportunity/
│   │   │   ├── strategy/
│   │   │   ├── options/
│   │   │   ├── portfolio/          # Portfolio Intelligence
│   │   │   ├── allocation/         # Capital Allocation
│   │   │   ├── cost/               # Opportunity Cost
│   │   │   ├── replacement/        # Trade Replacement
│   │   │   ├── risk/
│   │   │   ├── trading/            # Trade Execution
│   │   │   ├── positions/          # Position Management
│   │   │   ├── monitoring/         # Portfolio Monitoring
│   │   │   └── ai_manager/
│   │   ├── core/           # Config, DB, Redis clients
│   │   ├── models/         # Shared Pydantic schemas
│   │   ├── main.py
│   │   └── celery_app.py
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Next.js app
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # Dashboard
│   │   ├── opportunities/
│   │   ├── portfolio/
│   │   ├── positions/[id]/
│   │   ├── reports/
│   │   └── settings/
│   ├── components/
│   │   ├── shared/         # DataTable, ScoreBadge, RegimeDot, etc.
│   │   ├── dashboard/
│   │   ├── opportunities/
│   │   ├── portfolio/
│   │   └── reports/
│   ├── lib/
│   │   ├── api.ts          # API client
│   │   └── utils.ts        # Formatting, helpers
│   ├── tailwind.config.ts
│   ├── Dockerfile
│   └── package.json
├── data/                   # Mounted volume for DuckDB + Parquet
│   ├── market_data/
│   ├── signals/
│   └── portfolio.db
├── docker-compose.yml
├── .github/workflows/deploy.yml
└── README.md
```

## Implementation Order (7 Phases)

| Phase | Scope | Timeline |
|---|---|---|
| 1 | Data Engine + Backend skeleton + Docker + DB schema | Week 1-2 |
| 2 | Feature Engineering + Regime + CUSUM + Breakout | Week 2-3 |
| 3 | Opportunity Ranking + Strategy Selection + Options Engine | Week 3-4 |
| 4 | Portfolio Intelligence + Capital Allocation + Risk + Cost + Replacement | Week 4-5 |
| 5 | Alpaca integration + Trade Execution + Position Management + Monitoring | Week 5-6 |
| 6 | AI Portfolio Manager + Self-Learning + Frontend | Week 6-8 |
| 7 | OCI deployment + CI/CD + Advanced features (Monte Carlo, stress testing) | Week 8+ |
