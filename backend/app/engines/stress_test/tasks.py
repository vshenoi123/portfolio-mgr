from celery import shared_task
from app.engines.stress_test.service import StressTestService

service = StressTestService()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_weekly_stress_test(self):
    try:
        from app.engines.portfolio.service import load_portfolio_state
        from app.config import settings

        portfolio = load_portfolio_state(settings.database_path)
        positions = portfolio.get("positions", [])

        if not positions:
            return {"status": "no_positions", "message": "No positions to stress test"}

        position_dicts = []
        for pos in positions:
            if pos.get("asset_type") == "equity":
                position_dicts.append({
                    "ticker": pos.get("ticker", ""),
                    "beta": pos.get("beta", 1.0),
                    "market_value": pos.get("market_value", 0.0),
                    "sector": pos.get("sector", "Unknown"),
                })

        results = service.run_stress_test(position_dicts)
        return {
            "status": "success",
            "positions_tested": len(position_dicts),
            "scenarios_run": len(results),
        }
    except Exception as exc:
        raise self.retry(exc=exc)