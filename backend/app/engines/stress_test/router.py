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
        return [r.model_dump() for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stress-test/scenarios")
async def get_stress_scenarios():
    return service.available_scenarios()