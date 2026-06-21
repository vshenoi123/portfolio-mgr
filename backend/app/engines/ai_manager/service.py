import logging
from datetime import datetime, timezone, date
from app.config import settings
from app.engines.ai_manager.schemas import DailyReportResponse, ReportSection, RecommendationResponse
from app.engines.ai_manager.llm_provider import LLMFactory
from app.engines.ai_manager.prompts import build_daily_report_prompt, build_analysis_prompt

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self):
        self._provider = None

    @property
    def provider(self):
        if self._provider is None:
            try:
                self._provider = LLMFactory.create(
                    provider=getattr(settings, "llm_provider", "openai"),
                    api_key=getattr(settings, "openai_api_key", ""),
                )
            except Exception as e:
                logger.warning("LLM provider init failed: %s", e)
                self._provider = None
        return self._provider

    def generate_daily_report(self, report_date: date | None = None) -> DailyReportResponse:
        rd = report_date or date.today()
        sections = []
        if self.provider:
            try:
                prompt = build_daily_report_prompt("Portfolio: $100k, Cash: $25k", "AAPL: 85, NVDA: 78", "Health: 72/100", "Bull")
                content = self.provider.generate(prompt)
                sections = [ReportSection(title="AI Analysis", content=content)]
            except Exception as e:
                sections = [ReportSection(title="AI Analysis", content=f"Report generation unavailable: {e}", priority="low")]
        else:
            sections = [ReportSection(title="AI Analysis", content="AI provider not configured. Set OPENAI_API_KEY or OLLAMA_BASE_URL.", priority="low")]
        return DailyReportResponse(
            report_date=rd.isoformat(), sections=sections,
            summary="Daily portfolio report", generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def analyze_ticker(self, ticker: str, signals: dict, regime: str) -> RecommendationResponse:
        rec = RecommendationResponse(ticker=ticker, action="hold", confidence=0.5,
            reasoning="No LLM analysis available")
        if self.provider:
            try:
                prompt = build_analysis_prompt(ticker, signals, regime, "")
                content = self.provider.generate(prompt)
                rec.reasoning = content
            except Exception as e:
                rec.reasoning = f"Analysis unavailable: {e}"
        return rec

    def get_performance_attribution(self, period: str = "1m"):
        from app.engines.ai_manager.schemas import PerformanceAttribution
        return PerformanceAttribution(period=period)

    def get_self_learning_insights(self):
        return {"signal_efficacy": {}, "best_regime": "", "strategy_summary": {}}
