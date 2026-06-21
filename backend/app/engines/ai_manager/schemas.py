from __future__ import annotations
from datetime import date
from pydantic import BaseModel


class ReportSection(BaseModel):
    title: str
    content: str
    priority: str = "normal"
    details: dict = {}


class DailyReportRequest(BaseModel):
    report_date: date | None = None


class DailyReportResponse(BaseModel):
    report_date: str
    sections: list[ReportSection] = []
    summary: str = ""
    generated_at: str = ""
    engine_version: str = "1.0.0"


class RecommendationRequest(BaseModel):
    ticker: str
    context: dict = {}


class RecommendationResponse(BaseModel):
    ticker: str
    action: str = "hold"
    confidence: float = 0.5
    reasoning: str = ""
    details: dict = {}


class PerformanceAttribution(BaseModel):
    period: str = "1m"
    total_return_pct: float = 0.0
    best_performer: str = ""
    worst_performer: str = ""
    strategy_breakdown: dict = {}
    sector_breakdown: dict = {}
    details: dict = {}
