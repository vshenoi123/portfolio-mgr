def build_daily_report_prompt(state_summary: str, opportunities: str,
                               risk_assessment: str, regime_data: str) -> str:
    return f"""You are an AI Portfolio Manager. Generate a concise daily portfolio report.

Current Portfolio State:
{state_summary}

Top Opportunities:
{opportunities}

Risk Assessment:
{risk_assessment}

Market Regime:
{regime_data}

Provide: 1) Executive Summary (2-3 bullet points), 2) Portfolio Health assessment,
3) Key Opportunities, 4) Risk Alerts, 5) Recommended Actions for today."""


def build_analysis_prompt(ticker: str, signals: dict, regime: str,
                           portfolio_context: str) -> str:
    return f"""Analyze {ticker} for portfolio action.

Signals: {signals}
Regime: {regime}
Portfolio Context: {portfolio_context}

Provide: 1) Action recommendation, 2) Confidence level, 3) Reasoning."""
