import logging
from fastapi import APIRouter

from app.engines.ai_manager.schemas import DailyReportRequest
from app.engines.ai_manager.service import ReportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/report")
def generate_report(req: DailyReportRequest):
    logger.info("Generating daily report (date=%s)", req.report_date)
    service = ReportService()
    report = service.generate_daily_report(report_date=req.report_date)
    logger.info("Report generated: %d sections, summary=%d chars", len(report.sections), len(report.summary))
    return report.model_dump()


@router.get("/report")
def get_report():
    logger.info("Generating daily report (auto date)")
    service = ReportService()
    report = service.generate_daily_report()
    logger.info("Report generated: %d sections, summary=%d chars", len(report.sections), len(report.summary))
    return report.model_dump()


@router.post("/analyze/{ticker}")
def analyze_ticker(ticker: str, signals: dict = {}, regime: str = "Unknown"):
    service = ReportService()
    result = service.analyze_ticker(ticker, signals, regime)
    return result.model_dump()
