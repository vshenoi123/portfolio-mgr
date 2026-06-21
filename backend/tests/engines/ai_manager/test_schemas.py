from datetime import date, datetime


class TestReportSection:
    def test_default_construction(self):
        from app.engines.ai_manager.schemas import ReportSection
        rs = ReportSection(title="Test", content="Content")
        assert rs.title == "Test"
        assert rs.priority == "normal"
        assert rs.details == {}

    def test_full_construction(self):
        from app.engines.ai_manager.schemas import ReportSection
        rs = ReportSection(title="Risk Alert", content="High volatility",
                           priority="high", details={"score": 85})
        assert rs.priority == "high"
        assert rs.details["score"] == 85


class TestDailyReportRequest:
    def test_default_date_is_none(self):
        from app.engines.ai_manager.schemas import DailyReportRequest
        req = DailyReportRequest()
        assert req.report_date is None

    def test_with_date(self):
        from app.engines.ai_manager.schemas import DailyReportRequest
        req = DailyReportRequest(report_date=date(2024, 12, 1))
        assert req.report_date == date(2024, 12, 1)


class TestDailyReportResponse:
    def test_default_construction(self):
        from app.engines.ai_manager.schemas import DailyReportResponse
        resp = DailyReportResponse(report_date="2024-12-01")
        assert resp.report_date == "2024-12-01"
        assert resp.sections == []
        assert resp.summary == ""
        assert resp.engine_version == "1.0.0"

    def test_with_sections(self):
        from app.engines.ai_manager.schemas import DailyReportResponse, ReportSection
        section = ReportSection(title="Exec Summary", content="Good day")
        resp = DailyReportResponse(
            report_date="2024-12-01", sections=[section],
            summary="Positive day", generated_at=datetime.now().isoformat(),
        )
        assert len(resp.sections) == 1
        assert resp.sections[0].title == "Exec Summary"


class TestRecommendationRequest:
    def test_default_context(self):
        from app.engines.ai_manager.schemas import RecommendationRequest
        req = RecommendationRequest(ticker="AAPL")
        assert req.ticker == "AAPL"
        assert req.context == {}

    def test_with_context(self):
        from app.engines.ai_manager.schemas import RecommendationRequest
        req = RecommendationRequest(ticker="MSFT", context={"regime": "Bull"})
        assert req.context["regime"] == "Bull"


class TestRecommendationResponse:
    def test_default_construction(self):
        from app.engines.ai_manager.schemas import RecommendationResponse
        resp = RecommendationResponse(ticker="AAPL")
        assert resp.action == "hold"
        assert resp.confidence == 0.5

    def test_buy_recommendation(self):
        from app.engines.ai_manager.schemas import RecommendationResponse
        resp = RecommendationResponse(ticker="NVDA", action="buy",
                                      confidence=0.85, reasoning="Strong momentum")
        assert resp.action == "buy"
        assert resp.confidence == 0.85
        assert resp.reasoning == "Strong momentum"


class TestPerformanceAttribution:
    def test_default_construction(self):
        from app.engines.ai_manager.schemas import PerformanceAttribution
        pa = PerformanceAttribution()
        assert pa.period == "1m"
        assert pa.total_return_pct == 0.0

    def test_full_construction(self):
        from app.engines.ai_manager.schemas import PerformanceAttribution
        pa = PerformanceAttribution(
            period="3m", total_return_pct=12.5,
            best_performer="NVDA", worst_performer="INTC",
            strategy_breakdown={"momentum": 8.0},
            sector_breakdown={"TECHNOLOGY": 10.0},
        )
        assert pa.period == "3m"
        assert pa.total_return_pct == 12.5
        assert pa.best_performer == "NVDA"
