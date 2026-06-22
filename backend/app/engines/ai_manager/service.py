import glob
import json
import logging
import os
import time
from datetime import datetime, timezone, date
from app.config import settings
from app.database import get_data_dir
from app.engines.ai_manager.schemas import DailyReportResponse, ReportSection, RecommendationResponse
from app.engines.ai_manager.llm_provider import LLMFactory
from app.engines.ai_manager.prompts import build_daily_report_prompt, build_analysis_prompt

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5


def _market_scan_ts():
    scan_dir = os.path.join(get_data_dir(), "signals", "market_scan")
    files = sorted(glob.glob(os.path.join(scan_dir, "*.parquet")))
    if not files:
        return 0
    return int(os.path.getmtime(files[-1]))


class ReportService:
    def __init__(self):
        self._provider = None
        self._report_cache: dict[str, DailyReportResponse] = {}

    @property
    def provider(self):
        if self._provider is None:
            try:
                prov = getattr(settings, "llm_provider", "openai")
                if prov == "gemini":
                    api_key = getattr(settings, "google_api_key", "")
                else:
                    api_key = getattr(settings, "openai_api_key", "")
                self._provider = LLMFactory.create(
                    provider=prov, api_key=api_key,
                    model=getattr(settings, "gemini_model", "gemini-2.0-flash-lite"),
                    base_url=getattr(settings, "ollama_base_url", "http://localhost:11434"),
                )
            except Exception as e:
                logger.warning("LLM provider init failed: %s", e)
                self._provider = None
        return self._provider

    def generate_daily_report(self, report_date: date | None = None) -> DailyReportResponse:
        rd = report_date or date.today()
        data_ts = _market_scan_ts()
        cache_key = f"{rd.isoformat()}_{data_ts}"

        cached = self._report_cache.get(cache_key)
        if cached:
            return cached

        disk_cached = self._load_cached_report(cache_key)
        if disk_cached:
            self._report_cache[cache_key] = disk_cached
            return disk_cached

        sections = []
        if self.provider:
            prompt = build_daily_report_prompt("Portfolio: $100k, Cash: $25k", "AAPL: 85, NVDA: 78", "Health: 72/100", "Bull")
            for attempt in range(MAX_RETRIES):
                try:
                    content = self.provider.generate(prompt)
                    sections = [ReportSection(title="AI Analysis", content=content)]
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str and "retry" in err_str:
                        delay = RETRY_DELAY * (attempt + 1)
                        logger.warning("Rate limited (attempt %d/%d), retrying in %ds: %s",
                                       attempt + 1, MAX_RETRIES, delay, err_str[:120])
                        time.sleep(delay)
                    else:
                        sections = [ReportSection(title="AI Analysis", content=f"Report generation unavailable: {e}", priority="low")]
                        break
            else:
                sections = [ReportSection(title="AI Analysis", content="Report generation unavailable: daily LLM quota exceeded. Try again tomorrow or use a different API key.", priority="low")]
        else:
            sections = [ReportSection(title="AI Analysis", content="AI provider not configured. Set OPENAI_API_KEY, GOOGLE_API_KEY, or OLLAMA_BASE_URL.", priority="low")]

        result = DailyReportResponse(
            report_date=rd.isoformat(), sections=sections,
            summary="Daily portfolio report", generated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._report_cache[cache_key] = result
        self._save_cached_report(cache_key, result)
        return result

    def _cache_path(self, cache_key: str) -> str:
        cache_dir = os.path.join(get_data_dir(), "cache", "reports")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{cache_key}.json")

    def _load_cached_report(self, cache_key: str) -> DailyReportResponse | None:
        path = self._cache_path(cache_key)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return DailyReportResponse(**data)
        except Exception:
            return None

    def _save_cached_report(self, cache_key: str, report: DailyReportResponse) -> None:
        try:
            with open(self._cache_path(cache_key), "w") as f:
                json.dump(report.model_dump(), f)
        except Exception as e:
            logger.warning("Failed to cache report: %s", e)

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
