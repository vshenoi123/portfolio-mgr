from unittest.mock import patch, MagicMock


class TestOpportunityTasks:
    @patch("app.engines.opportunity.tasks.build_opportunity_scores")
    @patch("app.engines.opportunity.tasks.ScoringRefinementModel")
    def test_compute_opportunities_task(self, mock_model_cls, mock_build):
        from app.engines.opportunity.tasks import compute_opportunities
        from app.engines.opportunity.schemas import OpportunityScore
        mock_model_cls.return_value = MagicMock()
        mock_build.return_value = [
            OpportunityScore(ticker="AAPL", total_score=75.0),
            OpportunityScore(ticker="NVDA", total_score=82.0),
        ]
        result = compute_opportunities()
        assert result["status"] == "success"
        assert result["opportunities_count"] == 2

    @patch("app.engines.opportunity.tasks.build_opportunity_scores")
    def test_compute_opportunities_empty(self, mock_build):
        from app.engines.opportunity.tasks import compute_opportunities
        mock_build.return_value = []
        result = compute_opportunities()
        assert result["status"] == "success"
        assert result["opportunities_count"] == 0

    @patch("app.engines.opportunity.tasks.build_opportunity_scores")
    def test_compute_opportunities_error(self, mock_build):
        from app.engines.opportunity.tasks import compute_opportunities
        mock_build.side_effect = Exception("Processing error")
        result = compute_opportunities()
        assert result["status"] == "error"
