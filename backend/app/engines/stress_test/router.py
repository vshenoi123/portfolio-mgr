from fastapi import APIRouter, HTTPException
from app.engines.stress_test.schemas import StressTestRequest
from app.engines.stress_test.service import StressTestService

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])
service = StressTestService()


@router.post("/stress-test")
async def run_stress_test(req: StressTestRequest):
    try:
        results = service.run_stress_test(
            positions=[p.model_dump() for p in req.positions],
            scenarios=req.scenarios,
            custom_scenarios=req.custom_scenarios,
        )
        return {"results": [r.model_dump() for r in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stress-test/run")
async def run_stress_test_now():
    """Run stress test on current portfolio positions."""
    import duckdb
    from app.config import settings
    from app.engines.stress_test.schemas import PortfolioPosition

    conn = duckdb.connect(settings.database_path)
    try:
        rows = conn.execute(
            "SELECT ticker, quantity, market_value, beta FROM positions"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"results": [], "message": "No positions to stress test"}

    positions = [
        PortfolioPosition(
            ticker=r[0],
            market_value=abs(float(r[2])) if r[2] else 0,
            beta=float(r[3]) if r[3] else 1.0,
        ).model_dump()
        for r in rows
    ]

    results = service.run_stress_test(positions=positions)
    return {"results": [r.model_dump() for r in results], "positions_tested": len(positions)}


@router.get("/stress-test/scenarios")
async def get_stress_scenarios():
    return service.available_scenarios()