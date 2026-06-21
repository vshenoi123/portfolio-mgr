import logging
from fastapi import APIRouter

from app.engines.ai_manager.schemas import DailyReportRequest
from app.engines.ai_manager.service import ReportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/report")
def generate_report(req: DailyReportRequest):
    service = ReportService()
    report = service.generate_daily_report(report_date=req.report_date)
    return report.model_dump()


@router.get("/report")
def get_report():
    service = ReportService()
    report = service.generate_daily_report()
    return report.model_dump()


@router.post("/analyze/{ticker}")
def analyze_ticker(ticker: str, signals: dict = {}, regime: str = "Unknown"):
    service = ReportService()
    result = service.analyze_ticker(ticker, signals, regime)
    return result.model_dump()
