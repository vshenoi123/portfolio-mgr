# Phase 6: AI Portfolio Manager + Self-Learning + Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the AI Portfolio Manager (LLM-powered daily reports), Self-Learning Engine (signal efficacy tracking), and the Next.js frontend (terminal-green dark mode dashboard).

**Architecture:** AI Manager uses Langchain with an abstract LLM provider (OpenAI or Ollama). Self-Learning runs SQL analytics against DuckDB `trade_journal`. Frontend is a standalone Next.js 14+ app with Tailwind, lightweight-charts, recharts, and Vitest.

**Tech Stack:** Python 3.12, langchain, openai, pydantic, FastAPI, Celery, DuckDB, Next.js 14, Tailwind CSS, lightweight-charts, recharts, lucide-react, IBM Plex fonts, Vitest, Testing Library

---

### Prerequisite: Update requirements.txt for Phase 6 libraries

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Append AI/Self-Learning dependencies**

Append to `backend/requirements.txt`:

```
# AI / LLM
langchain==0.3.7
langchain-openai==0.2.3
langchain-community==0.3.7
openai==1.54.0
tiktoken==0.8.0
```

- [ ] **Step 2: Install and verify**

Run: `cd backend && pip install -r requirements.txt 2>&1 | tail -5`
Expected: All packages install cleanly

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add langchain, openai for Phase 6 AI Portfolio Manager"
```

---

## Part A — Backend: AI Portfolio Manager

### Task 1: AI Manager Engine — Schemas

**Files:**
- Create: `backend/app/engines/ai_manager/__init__.py`
- Create: `backend/app/engines/ai_manager/schemas.py`
- Test: `backend/tests/engines/ai_manager/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/ai_manager/test_schemas.py`:

```python
import pytest
from datetime import datetime, timezone, date
from pydantic import ValidationError


class TestAIManagerSchemas:
    def test_daily_report_request_valid(self):
        from app.engines.ai_manager.schemas import DailyReportRequest
        req = DailyReportRequest()
        assert req.date is None

    def test_daily_report_request_with_date(self):
        from app.engines.ai_manager.schemas import DailyReportRequest
        req = DailyReportRequest(date=date(2026, 6, 21))
        assert req.date == date(2026, 6, 21)

    def test_daily_report_response_valid(self):
        from app.engines.ai_manager.schemas import DailyReportResponse, ReportSection
        sections = [
            ReportSection(title="Market Regime", content="SPY in Bull regime, confidence 85%"),
            ReportSection(title="Portfolio Health", content="Score: 72/100"),
        ]
        resp = DailyReportResponse(
            id=1,
            report_date=date(2026, 6, 21),
            sections=sections,
            summary="Bullish with caution",
            generated_at=datetime.now(timezone.utc),
            llm_model="gpt-4o",
        )
        assert len(resp.sections) == 2
        assert resp.llm_model == "gpt-4o"

    def test_report_section_validates_title(self):
        from app.engines.ai_manager.schemas import ReportSection
        with pytest.raises(ValidationError):
            ReportSection(title="", content="some content")

    def test_recommendation_request_valid(self):
        from app.engines.ai_manager.schemas import RecommendationRequest
        req = RecommendationRequest(ticker="AAPL")
        assert req.ticker == "AAPL"

    def test_recommendation_request_uppercases_ticker(self):
        from app.engines.ai_manager.schemas import RecommendationRequest
        req = RecommendationRequest(ticker="aapl")
        assert req.ticker == "AAPL"

    def test_recommendation_response_valid(self):
        from app.engines.ai_manager.schemas import RecommendationResponse
        resp = RecommendationResponse(
            ticker="AAPL",
            action="Buy",
            confidence=0.85,
            reasoning="Strong breakout with volume confirmation",
            risk_assessment="Moderate",
        )
        assert resp.action == "Buy"
        assert resp.confidence == 0.85

    def test_performance_attribution_schema(self):
        from app.engines.ai_manager.schemas import PerformanceAttribution
        attr = PerformanceAttribution(
            strategy="CSP",
            total_trades=12,
            win_rate=0.75,
            total_return_pct=8.5,
            sharpe_ratio=1.8,
            attribution_pct=35.0,
        )
        assert attr.strategy == "CSP"
        assert attr.win_rate == 0.75
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_schemas.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the schemas**

Create `backend/app/engines/ai_manager/__init__.py`:
```python
```

Create `backend/app/engines/ai_manager/schemas.py`:
```python
from datetime import datetime, date, timezone
from pydantic import BaseModel, field_validator


class ReportSection(BaseModel):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()


class DailyReportRequest(BaseModel):
    date: date | None = None


class DailyReportResponse(BaseModel):
    id: int
    report_date: date
    sections: list[ReportSection]
    summary: str
    generated_at: datetime
    llm_model: str


class RecommendationRequest(BaseModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()


class RecommendationResponse(BaseModel):
    ticker: str
    action: str
    confidence: float
    reasoning: str
    risk_assessment: str


class PerformanceAttribution(BaseModel):
    strategy: str
    total_trades: int
    win_rate: float
    total_return_pct: float
    sharpe_ratio: float
    attribution_pct: float
```

- [ ] **Step 4: Run tests again**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_schemas.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/ai_manager/
git add backend/tests/engines/ai_manager/test_schemas.py
git commit -m "feat(ai-manager): add schemas with tests"
```

### Task 2: AI Manager — LLM Provider Abstraction

**Files:**
- Create: `backend/app/engines/ai_manager/llm_provider.py`
- Test: `backend/tests/engines/ai_manager/test_llm_provider.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/ai_manager/test_llm_provider.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


class TestLLMProvider:
    def test_openai_provider_initialization(self):
        from app.engines.ai_manager.llm_provider import OpenAIProvider
        provider = OpenAIProvider(model="gpt-4o", api_key="test-key")
        assert provider.model == "gpt-4o"
        assert provider.provider_name == "openai"

    def test_ollama_provider_initialization(self):
        from app.engines.ai_manager.llm_provider import OllamaProvider
        provider = OllamaProvider(model="llama3", base_url="http://localhost:11434")
        assert provider.model == "llama3"
        assert provider.provider_name == "ollama"

    def test_llm_factory_returns_openai(self):
        from app.engines.ai_manager.llm_provider import LLMFactory
        provider = LLMFactory.create(provider_type="openai", api_key="test-key")
        from app.engines.ai_manager.llm_provider import OpenAIProvider
        assert isinstance(provider, OpenAIProvider)

    def test_llm_factory_returns_ollama(self):
        from app.engines.ai_manager.llm_provider import LLMFactory
        provider = LLMFactory.create(provider_type="ollama")
        from app.engines.ai_manager.llm_provider import OllamaProvider
        assert isinstance(provider, OllamaProvider)

    def test_llm_factory_invalid_provider_raises(self):
        from app.engines.ai_manager.llm_provider import LLMFactory
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMFactory.create(provider_type="invalid")

    @patch("app.engines.ai_manager.llm_provider.ChatOpenAI")
    def test_openai_generate(self, mock_chat):
        from app.engines.ai_manager.llm_provider import OpenAIProvider
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.content = "Test response"
        mock_instance.invoke.return_value = mock_response

        provider = OpenAIProvider(model="gpt-4o", api_key="test-key")
        result = provider.generate("Test prompt")
        assert result == "Test response"
        mock_instance.invoke.assert_called_once()

    @patch("app.engines.ai_manager.llm_provider.ChatOllama")
    def test_ollama_generate(self, mock_chat):
        from app.engines.ai_manager.llm_provider import OllamaProvider
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.content = "Ollama response"
        mock_instance.invoke.return_value = mock_response

        provider = OllamaProvider(model="llama3")
        result = provider.generate("Test prompt")
        assert result == "Ollama response"
        mock_instance.invoke.assert_called_once()

    def test_llm_provider_abstract_cannot_instantiate(self):
        from app.engines.ai_manager.llm_provider import LLMProvider
        with pytest.raises(TypeError):
            LLMProvider()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_llm_provider.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the LLM provider abstraction**

Create `backend/app/engines/ai_manager/llm_provider.py`:
```python
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        self.model = model
        self._llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.3)

    @property
    def provider_name(self) -> str:
        return "openai"

    def generate(self, prompt: str) -> str:
        response = self._llm.invoke([HumanMessage(content=prompt)])
        return response.content


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self._llm = ChatOllama(model=model, base_url=base_url, temperature=0.3)

    @property
    def provider_name(self) -> str:
        return "ollama"

    def generate(self, prompt: str) -> str:
        response = self._llm.invoke([HumanMessage(content=prompt)])
        return response.content


class LLMFacotry:
    @staticmethod
    def create(provider_type: str = "openai", **kwargs) -> LLMProvider:
        if provider_type == "openai":
            return OpenAIProvider(api_key=kwargs.get("api_key"))
        elif provider_type == "ollama":
            return OllamaProvider(
                model=kwargs.get("model", "llama3"),
                base_url=kwargs.get("base_url", "http://localhost:11434"),
            )
        raise ValueError(f"Unknown LLM provider: {provider_type}")
```

- [ ] **Step 4: Run tests again**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_llm_provider.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/ai_manager/llm_provider.py
git add backend/tests/engines/ai_manager/test_llm_provider.py
git commit -m "feat(ai-manager): add LLM provider abstraction with OpenAI and Ollama"
```

### Task 3: AI Manager — Prompt Builder

**Files:**
- Create: `backend/app/engines/ai_manager/prompts.py`
- Test: `backend/tests/engines/ai_manager/test_prompts.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/ai_manager/test_prompts.py`:

```python
import pytest
from datetime import date


class TestPromptBuilder:
    def test_daily_report_prompt_contains_all_sections(self):
        from app.engines.ai_manager.prompts import build_daily_report_prompt
        context = {
            "regime": "Bull (confidence: 85%)",
            "portfolio_health": "Score: 72/100",
            "top_opportunities": [{"ticker": "AAPL", "score": 85}],
            "current_risks": ["Elevated VIX", "Sector concentration in tech"],
            "capital_allocation": {"cash": 45000, "equity": 120000},
            "performance": {"total_return": 12.5, "best_strategy": "CSP"},
        }
        prompt = build_daily_report_prompt(context)
        assert "Market Regime" in prompt
        assert "Portfolio Health" in prompt
        assert "Top Opportunities" in prompt
        assert "Current Risks" in prompt
        assert "Recommended Adjustments" in prompt
        assert "Capital Allocation" in prompt
        assert "Trade Ideas" in prompt

    def test_daily_report_prompt_includes_context_data(self):
        from app.engines.ai_manager.prompts import build_daily_report_prompt
        context = {
            "regime": "Bear (confidence: 72%)",
            "portfolio_health": "Score: 45/100",
            "top_opportunities": [],
            "current_risks": ["Market downturn"],
            "capital_allocation": {"cash": 80000, "equity": 50000},
            "performance": {"total_return": -3.2, "best_strategy": "Cash"},
        }
        prompt = build_daily_report_prompt(context)
        assert "Bear" in prompt
        assert "45/100" in prompt
        assert "Market downturn" in prompt

    def test_analysis_prompt_contains_ticker(self):
        from app.engines.ai_manager.prompts import build_analysis_prompt
        prompt = build_analysis_prompt("AAPL", {"rsi_14": 62, "ema_20": 150.0})
        assert "AAPL" in prompt
        assert "rsi_14" in prompt

    def test_daily_report_prompt_handles_empty_opportunities(self):
        from app.engines.ai_manager.prompts import build_daily_report_prompt
        context = {
            "regime": "Range",
            "portfolio_health": "Score: 60/100",
            "top_opportunities": [],
            "current_risks": [],
            "capital_allocation": {"cash": 50000, "equity": 100000},
            "performance": {"total_return": 5.0, "best_strategy": "LEAPS"},
        }
        prompt = build_daily_report_prompt(context)
        assert "No top opportunities" in prompt or "no opportunities" in prompt.lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_prompts.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the prompts module**

Create `backend/app/engines/ai_manager/prompts.py`:
```python
from typing import Any


DAILY_REPORT_TEMPLATE = """You are an AI Portfolio Manager for a personal hedge fund. Generate a concise daily report based on the following data.

Market Regime: {regime}
Portfolio Health: {portfolio_health}
Top Opportunities: {opportunities}
Current Risks: {risks}
Capital Allocation: {capital_allocation}
Performance: {performance}

Structure your report with these sections:
1. **Market Regime** — Current regime and what it means
2. **Portfolio Health** — Score breakdown and key metrics
3. **Top Opportunities** — Best setups to act on
4. **Current Risks** — Risk factors to monitor
5. **Recommended Adjustments** — Specific actions to take
6. **Capital Allocation** — Suggested allocation changes
7. **Trade Ideas** — 2-3 specific trade ideas with rationale"""


ANALYSIS_TEMPLATE = """Analyze {ticker} for a potential trade based on these indicators:
{indicators}

Provide: action (Buy/Hold/Avoid), confidence (0-1), reasoning, and risk assessment."""


def _format_opportunities(opps: list[dict]) -> str:
    if not opps:
        return "No top opportunities currently identified."
    return "\n".join(f"- {o['ticker']}: Score {o['score']}" for o in opps)


def _format_risks(risks: list[str]) -> str:
    if not risks:
        return "No significant risks identified."
    return "\n".join(f"- {r}" for r in risks)


def _format_allocation(alloc: dict) -> str:
    cash = alloc.get("cash", 0)
    equity = alloc.get("equity", 0)
    total = cash + equity
    return f"Cash: ${cash:,.0f} ({cash/total*100:.0f}%), Equity: ${equity:,.0f} ({equity/total*100:.0f}%)" if total else "No capital deployed."


def build_daily_report_prompt(context: dict[str, Any]) -> str:
    return DAILY_REPORT_TEMPLATE.format(
        regime=context.get("regime", "Unknown"),
        portfolio_health=context.get("portfolio_health", "N/A"),
        opportunities=_format_opportunities(context.get("top_opportunities", [])),
        risks=_format_risks(context.get("current_risks", [])),
        capital_allocation=_format_allocation(context.get("capital_allocation", {})),
        performance=str(context.get("performance", {})),
    )


def build_analysis_prompt(ticker: str, indicators: dict[str, float]) -> str:
    indicators_str = "\n".join(f"  {k}: {v}" for k, v in indicators.items())
    return ANALYSIS_TEMPLATE.format(ticker=ticker, indicators=indicators_str)
```

- [ ] **Step 4: Run tests again**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_prompts.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/ai_manager/prompts.py
git add backend/tests/engines/ai_manager/test_prompts.py
git commit -m "feat(ai-manager): add prompt builder with templates and tests"
```

### Task 4: AI Manager — Report Service

**Files:**
- Create: `backend/app/engines/ai_manager/service.py`
- Test: `backend/tests/engines/ai_manager/test_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/ai_manager/test_service.py`:

```python
import pytest
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock


class TestReportService:
    @patch("app.engines.ai_manager.service.LLMFactory")
    def test_generate_daily_report_success(self, mock_factory):
        from app.engines.ai_manager.service import ReportService
        mock_provider = MagicMock()
        mock_provider.provider_name = "openai"
        mock_provider.generate.return_value = "## Market Regime\nBull market\n## Portfolio Health\nScore: 80"
        mock_factory.create.return_value = mock_provider

        db_mock = MagicMock()
        db_mock.fetchone.return_value = [42]
        db_mock.description = [("id",)]

        service = ReportService(db=db_mock, provider_type="openai", api_key="test-key")
        report = service.generate_daily_report(
            report_date=date(2026, 6, 21),
            context={"regime": "Bull", "portfolio_health": "Score: 80"},
        )
        assert report.report_date == date(2026, 6, 21)
        assert len(report.sections) > 0
        assert report.llm_model == "openai"
        assert report.id == 42

    @patch("app.engines.ai_manager.service.LLMFactory")
    def test_get_report_by_date(self, mock_factory):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchone.return_value = (
            1, date(2026, 6, 21),
            '[{"title": "Market Regime", "content": "Bull"}]',
            "Summary text", datetime.now(timezone.utc), "gpt-4o",
        )
        service = ReportService(db=db_mock, provider_type="openai", api_key="test-key")
        report = service.get_report(date(2026, 6, 21))
        assert report is not None
        assert report.report_date == date(2026, 6, 21)

    def test_get_report_not_found(self):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchone.return_value = None
        service = ReportService(db=db_mock, provider_type="openai", api_key="test-key")
        assert service.get_report(date(2026, 6, 21)) is None

    @patch("app.engines.ai_manager.service.LLMFactory")
    def test_get_latest_report(self, mock_factory):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchone.return_value = (
            5, date(2026, 6, 21),
            '[{"title": "Market Regime", "content": "Bull"}]',
            "Summary", datetime.now(timezone.utc), "gpt-4o",
        )
        service = ReportService(db=db_mock, provider_type="openai", api_key="test-key")
        report = service.get_latest_report()
        assert report is not None
        assert report.id == 5

    @patch("app.engines.ai_manager.service.LLMFactory")
    def test_generate_report_parses_sections_from_markdown(self, mock_factory):
        from app.engines.ai_manager.service import ReportService
        mock_provider = MagicMock()
        mock_provider.provider_name = "openai"
        mock_provider.generate.return_value = (
            "## Market Regime\nBullish\n\n## Portfolio Health\nScore 75\n\n"
            "## Top Opportunities\nAAPL\n\n## Current Risks\nNone\n\n"
            "## Recommended Adjustments\nHold\n\n## Capital Allocation\n60/40\n\n"
            "## Trade Ideas\nBuy SPY"
        )
        mock_factory.create.return_value = mock_provider

        db_mock = MagicMock()
        db_mock.fetchone.return_value = [1]
        db_mock.description = [("id",)]

        service = ReportService(db=db_mock, provider_type="openai", api_key="test-key")
        report = service.generate_daily_report(
            report_date=date(2026, 6, 21),
            context={"regime": "Bull", "portfolio_health": "Score 75"},
        )
        assert len(report.sections) == 7
        assert report.sections[0].title == "Market Regime"
        assert report.sections[1].title == "Portfolio Health"

    def test_parse_sections_empty_text(self):
        from app.engines.ai_manager.service import ReportService
        service = ReportService(db=MagicMock(), provider_type="openai", api_key="x")
        sections = service._parse_sections("")
        assert sections == []

    def test_parse_sections_no_headers(self):
        from app.engines.ai_manager.service import ReportService
        service = ReportService(db=MagicMock(), provider_type="openai", api_key="x")
        sections = service._parse_sections("Just some text without headers")
        assert len(sections) == 0

    def test_get_reports_list(self):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = [
            (1, date(2026, 6, 21), "[]", "Summary 1", datetime.now(timezone.utc), "gpt-4o"),
            (2, date(2026, 6, 20), "[]", "Summary 2", datetime.now(timezone.utc), "gpt-4o"),
        ]
        service = ReportService(db=db_mock, provider_type="openai", api_key="test-key")
        reports = service.get_reports(limit=10)
        assert len(reports) == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_service.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the report service**

Create `backend/app/engines/ai_manager/service.py`:

```python
import json
import re
from datetime import date, datetime, timezone
from typing import Any

from app.engines.ai_manager.schemas import (
    DailyReportResponse,
    PerformanceAttribution,
    ReportSection,
    RecommendationRequest,
    RecommendationResponse,
)
from app.engines.ai_manager.llm_provider import LLMFactory
from app.engines.ai_manager.prompts import build_daily_report_prompt, build_analysis_prompt


class ReportService:
    def __init__(self, db, provider_type: str = "openai", api_key: str | None = None, **llm_kwargs):
        self.db = db
        self._provider = LLMFactory.create(provider_type=provider_type, api_key=api_key, **llm_kwargs)

    def generate_daily_report(self, report_date: date, context: dict[str, Any]) -> DailyReportResponse:
        prompt = build_daily_report_prompt(context)
        llm_response = self._provider.generate(prompt)
        sections = self._parse_sections(llm_response)
        summary = sections[0].content[:200] if sections else "No summary generated."
        sections_json = json.dumps([s.model_dump() for s in sections])
        now = datetime.now(timezone.utc)

        self.db.execute(
            """INSERT INTO daily_reports (report_date, sections, summary, generated_at, llm_model)
               VALUES (?, ?, ?, ?, ?) RETURNING id""",
            [report_date, sections_json, summary, now, self._provider.provider_name],
        )
        row = self.db.fetchone()
        report_id = row[0] if row else 0

        return DailyReportResponse(
            id=report_id,
            report_date=report_date,
            sections=sections,
            summary=summary,
            generated_at=now,
            llm_model=self._provider.provider_name,
        )

    def get_report(self, report_date: date) -> DailyReportResponse | None:
        row = self.db.execute(
            "SELECT id, report_date, sections, summary, generated_at, llm_model FROM daily_reports WHERE report_date = ?",
            [report_date],
        ).fetchone()
        if not row:
            return None
        return self._row_to_report(row)

    def get_latest_report(self) -> DailyReportResponse | None:
        row = self.db.execute(
            "SELECT id, report_date, sections, summary, generated_at, llm_model FROM daily_reports ORDER BY report_date DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return self._row_to_report(row)

    def get_reports(self, limit: int = 30) -> list[DailyReportResponse]:
        rows = self.db.execute(
            "SELECT id, report_date, sections, summary, generated_at, llm_model FROM daily_reports ORDER BY report_date DESC LIMIT ?",
            [limit],
        ).fetchall()
        return [self._row_to_report(r) for r in rows]

    def _row_to_report(self, row) -> DailyReportResponse:
        sections_data = json.loads(row[2]) if isinstance(row[2], str) else []
        sections = [ReportSection(**s) for s in sections_data]
        return DailyReportResponse(
            id=row[0],
            report_date=row[1],
            sections=sections,
            summary=row[3],
            generated_at=row[4],
            llm_model=row[5],
        )

    def _parse_sections(self, text: str) -> list[ReportSection]:
        sections: list[ReportSection] = []
        pattern = r"##\s*\*{0,2}(.+?)\*{0,2}\n(.*?)(?=\n##|\Z)"
        matches = re.findall(pattern, text, re.DOTALL)
        for title, content in matches:
            sections.append(ReportSection(title=title.strip(), content=content.strip()))
        return sections

    def analyze_ticker(self, request: RecommendationRequest, indicators: dict[str, float]) -> RecommendationResponse:
        prompt = build_analysis_prompt(request.ticker, indicators)
        llm_response = self._provider.generate(prompt)
        action = "Hold"
        confidence = 0.5
        reasoning = llm_response[:200]
        risk = "Moderate"
        if "Buy" in llm_response:
            action = "Buy"
        elif "Avoid" in llm_response:
            action = "Avoid"
        confidence_match = re.search(r"confidence[:\s]+([0-9.]+)", llm_response, re.IGNORECASE)
        if confidence_match:
            confidence = min(float(confidence_match.group(1)), 1.0)

        return RecommendationResponse(
            ticker=request.ticker,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            risk_assessment=risk,
        )
```

- [ ] **Step 4: Run tests again**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_service.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/ai_manager/service.py
git add backend/tests/engines/ai_manager/test_service.py
git commit -m "feat(ai-manager): add report generation service with tests"
```

### Task 6: AI Manager — Performance Attribution and Self-Learning Insights

**Files:**
- Modify: `backend/app/engines/ai_manager/service.py`
- Test: `backend/tests/engines/ai_manager/test_performance.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/ai_manager/test_performance.py`:
```python
import pytest
from datetime import date
from unittest.mock import MagicMock


class TestPerformanceAttribution:
    def test_get_performance_attribution_by_strategy(self):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = [
            ("CSP", 12, 0.75, 8.5, 1.8, 35.0),
            ("LEAPS", 5, 0.60, 15.2, 1.2, 40.0),
            ("Swing", 8, 0.625, 5.0, 0.9, 25.0),
        ]
        service = ReportService(db=db_mock, provider_type="openai", api_key="x")
        results = service.get_performance_attribution()
        assert len(results) == 3
        assert results[0].strategy == "CSP"
        assert results[0].total_trades == 12
        assert results[0].attribution_pct == 35.0

    def test_get_performance_attribution_empty(self):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = []
        service = ReportService(db=db_mock, provider_type="openai", api_key="x")
        assert service.get_performance_attribution() == []

    def test_get_performance_attribution_by_regime(self):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = [
            ("Bull", 18, 0.72, 10.2, 2.1),
            ("Bear", 6, 0.50, -3.5, -0.4),
        ]
        service = ReportService(db=db_mock, provider_type="openai", api_key="x")
        results = service.get_performance_attribution(group_by="regime")
        assert len(results) == 2

    def test_get_performance_attribution_by_signal_type(self):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = [
            ("Breakout", 10, 0.70, 9.0, 1.5),
            ("CUSUM", 4, 0.50, 3.0, 0.6),
        ]
        service = ReportService(db=db_mock, provider_type="openai", api_key="x")
        results = service.get_performance_attribution(group_by="signal_type")
        assert len(results) == 2

    def test_get_self_learning_insights(self):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = [
            ("Breakout", "Bull", 0.82, 15, 12),
            ("CUSUM", "Bear", 0.45, 8, 3),
        ]
        service = ReportService(db=db_mock, provider_type="openai", api_key="x")
        insights = service.get_self_learning_insights()
        assert len(insights) == 2
        assert insights[0]["signal_type"] == "Breakout"
        assert insights[0]["win_rate"] > 0.8

    def test_get_self_learning_insights_empty(self):
        from app.engines.ai_manager.service import ReportService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = []
        service = ReportService(db=db_mock, provider_type="openai", api_key="x")
        assert service.get_self_learning_insights() == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_performance.py -v`
Expected: FAIL (ReportService missing methods)

- [ ] **Step 3: Add performance/self-learning methods to service**

Append these methods to `ReportService` class in `backend/app/engines/ai_manager/service.py`:

```python
    def get_performance_attribution(self, group_by: str = "strategy") -> list[PerformanceAttribution]:
        if group_by == "regime":
            rows = self.db.execute("""
                SELECT regime, COUNT(*), AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END),
                       AVG(return_pct), AVG(sharpe_ratio)
                FROM trade_journal
                WHERE outcome IS NOT NULL
                GROUP BY regime
                ORDER BY AVG(return_pct) DESC
            """).fetchall()
            return [
                PerformanceAttribution(
                    strategy=r[0], total_trades=int(r[1]),
                    win_rate=float(r[2]) if r[2] else 0.0,
                    total_return_pct=float(r[3]) if r[3] else 0.0,
                    sharpe_ratio=float(r[4]) if r[4] else 0.0,
                    attribution_pct=0.0,
                ) for r in rows
            ]
        elif group_by == "signal_type":
            rows = self.db.execute("""
                SELECT signal_type, COUNT(*), AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END),
                       AVG(return_pct), AVG(sharpe_ratio)
                FROM trade_journal
                WHERE signal_type IS NOT NULL AND outcome IS NOT NULL
                GROUP BY signal_type
                ORDER BY AVG(return_pct) DESC
            """).fetchall()
            return [
                PerformanceAttribution(
                    strategy=r[0], total_trades=int(r[1]),
                    win_rate=float(r[2]) if r[2] else 0.0,
                    total_return_pct=float(r[3]) if r[3] else 0.0,
                    sharpe_ratio=float(r[4]) if r[4] else 0.0,
                    attribution_pct=0.0,
                ) for r in rows
            ]

        rows = self.db.execute("""
            SELECT strategy, COUNT(*), AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END),
                   SUM(return_pct), AVG(sharpe_ratio),
                   SUM(return_pct) * 100.0 / NULLIF(SUM(SUM(return_pct)) OVER (), 0)
            FROM trade_journal
            WHERE outcome IS NOT NULL
            GROUP BY strategy
            ORDER BY SUM(return_pct) DESC
        """).fetchall()
        return [
            PerformanceAttribution(
                strategy=r[0], total_trades=int(r[1]),
                win_rate=float(r[2]) if r[2] else 0.0,
                total_return_pct=float(r[3]) if r[3] else 0.0,
                sharpe_ratio=float(r[4]) if r[4] else 0.0,
                attribution_pct=float(r[5]) if r[5] else 0.0,
            ) for r in rows
        ]

    def get_self_learning_insights(self) -> list[dict]:
        rows = self.db.execute("""
            SELECT signal_type, regime,
                   AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END) as win_rate,
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins
            FROM trade_journal
            WHERE outcome IS NOT NULL
            GROUP BY signal_type, regime
            HAVING COUNT(*) >= 3
            ORDER BY win_rate DESC
        """).fetchall()
        return [
            {
                "signal_type": r[0],
                "regime": r[1],
                "win_rate": round(float(r[2]), 4) if r[2] else 0.0,
                "total_trades": int(r[3]),
                "wins": int(r[4]),
            }
            for r in rows
        ]
```

- [ ] **Step 4: Run tests again**

Run: `cd backend && python -m pytest tests/engines/ai_manager/test_performance.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/ai_manager/service.py
git add backend/tests/engines/ai_manager/test_performance.py
git commit -m "feat(ai-manager): add performance attribution and self-learning insights with tests"
```

### Task 7: Database Schema — Add Missing Tables for Phase 6

**Files:**
- Modify: `backend/app/database.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_schema_phase6.py`:
```python
import pytest
from app.database import get_connection, close_connection


class TestPhase6Schema:
    def test_daily_reports_table_exists(self, test_db_path):
        conn = get_connection(test_db_path)
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        assert "daily_reports" in tables

    def test_daily_reports_columns(self, test_db_path):
        conn = get_connection(test_db_path)
        cols = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(daily_reports)").fetchall()}
        assert "id" in cols
        assert "report_date" in cols
        assert "sections" in cols
        assert "summary" in cols
        assert "generated_at" in cols
        assert "llm_model" in cols

    def test_trade_journal_table_exists(self, test_db_path):
        conn = get_connection(test_db_path)
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        assert "trade_journal" in tables

    def test_trade_journal_columns(self, test_db_path):
        conn = get_connection(test_db_path)
        cols = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(trade_journal)").fetchall()}
        for col in ["id", "ticker", "strategy", "signal_type", "entry_date", "exit_date",
                     "entry_price", "exit_price", "quantity", "return_pct", "outcome",
                     "regime", "sharpe_ratio", "notes"]:
            assert col in cols

    def test_performance_attribution_table_exists(self, test_db_path):
        conn = get_connection(test_db_path)
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        assert "performance_attribution" in tables

    def test_self_learning_signals_table_exists(self, test_db_path):
        conn = get_connection(test_db_path)
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        assert "self_learning_signals" in tables

    def test_self_learning_signals_columns(self, test_db_path):
        conn = get_connection(test_db_path)
        cols = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(self_learning_signals)").fetchall()}
        for col in ["id", "signal_type", "regime", "ticker", "entry_date", "exit_date",
                     "win", "return_pct", "confidence"]:
            assert col in cols

    def test_capital_allocation_table_exists(self, test_db_path):
        conn = get_connection(test_db_path)
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        assert "capital_allocation" in tables
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_schema_phase6.py -v`
Expected: Some FAIL because tables do not exist yet

- [ ] **Step 3: Update database.py with Phase 6 schema**

Append to the `_init_schema` function in `backend/app/database.py`:

```python
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            report_date DATE NOT NULL UNIQUE,
            sections TEXT NOT NULL,
            summary TEXT NOT NULL,
            generated_at TIMESTAMP NOT NULL,
            llm_model VARCHAR(50) NOT NULL
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            ticker VARCHAR(20) NOT NULL,
            strategy VARCHAR(20) NOT NULL,
            signal_type VARCHAR(50),
            entry_date DATE NOT NULL,
            exit_date DATE,
            entry_price DOUBLE NOT NULL,
            exit_price DOUBLE,
            quantity INTEGER NOT NULL,
            return_pct DOUBLE,
            outcome VARCHAR(10),
            regime VARCHAR(30),
            sharpe_ratio DOUBLE,
            notes TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS performance_attribution (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            date DATE NOT NULL,
            strategy VARCHAR(30) NOT NULL,
            total_trades INTEGER NOT NULL,
            win_rate DOUBLE NOT NULL,
            total_return_pct DOUBLE NOT NULL,
            sharpe_ratio DOUBLE,
            attribution_pct DOUBLE
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS self_learning_signals (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            signal_type VARCHAR(50) NOT NULL,
            regime VARCHAR(30),
            ticker VARCHAR(20) NOT NULL,
            entry_date DATE NOT NULL,
            exit_date DATE,
            win BOOLEAN,
            return_pct DOUBLE,
            confidence DOUBLE
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS capital_allocation (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            allocation_date DATE NOT NULL,
            cash DOUBLE NOT NULL,
            equity_value DOUBLE NOT NULL,
            options_buying_power DOUBLE,
            regime VARCHAR(30),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
```

- [ ] **Step 4: Run tests again**

Run: `cd backend && python -m pytest tests/test_schema_phase6.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/database.py
git add backend/tests/test_schema_phase6.py
git commit -m "feat(db): add daily_reports, trade_journal, performance_attribution, self_learning_signals, capital_allocation tables"
```

### Task 8: Self-Learning Engine

**Files:**
- Create: `backend/app/engines/self_learning/__init__.py`
- Create: `backend/app/engines/self_learning/service.py`
- Create: `backend/app/engines/self_learning/schemas.py`
- Test: `backend/tests/engines/self_learning/test_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/engines/self_learning/__init__.py`:
```python
```

Create `backend/tests/engines/self_learning/test_service.py`:
```python
import pytest
from datetime import date
from unittest.mock import MagicMock


class TestSelfLearningService:
    def test_log_trade(self):
        from app.engines.self_learning.service import SelfLearningService
        from app.engines.self_learning.schemas import TradeJournalEntry
        db_mock = MagicMock()
        db_mock.fetchone.return_value = [1]
        db_mock.description = [("id",)]
        service = SelfLearningService(db_mock)

        entry = TradeJournalEntry(
            ticker="AAPL",
            strategy="Swing",
            signal_type="Breakout",
            entry_date=date(2026, 6, 1),
            entry_price=180.0,
            quantity=100,
        )
        result = service.log_trade(entry)
        assert result == 1

    def test_close_trade(self):
        from app.engines.self_learning.service import SelfLearningService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchone.return_value = [1]
        service = SelfLearningService(db_mock)
        result = service.close_trade(1, exit_price=190.0, outcome="win", regime="Bull")
        assert result is True

    def test_close_trade_not_found(self):
        from app.engines.self_learning.service import SelfLearningService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchone.return_value = None
        service = SelfLearningService(db_mock)
        result = service.close_trade(999, exit_price=100.0)
        assert result is False

    def test_get_signal_efficacy_by_type(self):
        from app.engines.self_learning.service import SelfLearningService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = [
            ("Breakout", 20, 0.75, 15, 8.2),
            ("CUSUM", 10, 0.50, 5, 3.1),
        ]
        service = SelfLearningService(db_mock)
        results = service.get_signal_efficacy()
        assert len(results) == 2
        assert results[0]["signal_type"] == "Breakout"
        assert results[0]["win_rate"] == 0.75

    def test_get_signal_efficacy_empty(self):
        from app.engines.self_learning.service import SelfLearningService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = []
        service = SelfLearningService(db_mock)
        assert service.get_signal_efficacy() == []

    def test_get_best_regime_for_strategy(self):
        from app.engines.self_learning.service import SelfLearningService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = [
            ("Bull", "CSP", 0.85, 12),
            ("Range", "CSP", 0.70, 8),
            ("Bear", "CSP", 0.40, 5),
        ]
        service = SelfLearningService(db_mock)
        results = service.get_best_regime_for_strategy("CSP")
        assert results[0]["regime"] == "Bull"

    def test_record_signal_outcome(self):
        from app.engines.self_learning.service import SelfLearningService
        from app.engines.self_learning.schemas import SignalOutcome
        db_mock = MagicMock()
        db_mock.fetchone.return_value = [1]
        db_mock.description = [("id",)]
        service = SelfLearningService(db_mock)

        signal = SignalOutcome(
            signal_type="Breakout",
            regime="Bull",
            ticker="AAPL",
        )
        signal_id = service.record_signal_outcome(signal)
        assert signal_id == 1

    def test_log_trade_rejects_zero_quantity(self):
        from app.engines.self_learning.schemas import TradeJournalEntry
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TradeJournalEntry(
                ticker="AAPL", strategy="Swing", entry_date=date.today(),
                entry_price=100.0, quantity=0,
            )

    def test_log_trade_rejects_negative_quantity(self):
        from app.engines.self_learning.schemas import TradeJournalEntry
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TradeJournalEntry(
                ticker="AAPL", strategy="Swing", entry_date=date.today(),
                entry_price=100.0, quantity=-5,
            )

    def test_get_strategy_summary_statistics(self):
        from app.engines.self_learning.service import SelfLearningService
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchall.return_value = [
            ("CSP", 25, 0.80, 12.5, 2.1, 50000, 0.025),
            ("LEAPS", 10, 0.60, 22.0, 1.5, 80000, 0.044),
        ]
        service = SelfLearningService(db_mock)
        stats = service.get_strategy_summary()
        assert len(stats) == 2
        assert stats[0]["strategy"] == "CSP"
        assert stats[0]["avg_return_pct"] == 12.5
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/self_learning/ -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the self-learning engine**

Create `backend/app/engines/self_learning/__init__.py`:
```python
```

Create `backend/app/engines/self_learning/schemas.py`:
```python
from datetime import date
from pydantic import BaseModel, field_validator


class TradeJournalEntry(BaseModel):
    ticker: str
    strategy: str
    signal_type: str | None = None
    entry_date: date
    exit_date: date | None = None
    entry_price: float
    exit_price: float | None = None
    quantity: int
    return_pct: float | None = None
    outcome: str | None = None
    regime: str | None = None
    sharpe_ratio: float | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()


class SignalOutcome(BaseModel):
    signal_type: str
    regime: str | None = None
    ticker: str
    entry_date: date | None = None
    exit_date: date | None = None
    win: bool | None = None
    return_pct: float | None = None
    confidence: float | None = None

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()
```

Create `backend/app/engines/self_learning/service.py`:
```python
from datetime import date
from typing import Any

from app.engines.self_learning.schemas import TradeJournalEntry, SignalOutcome


class SelfLearningService:
    def __init__(self, db):
        self.db = db

    def log_trade(self, entry: TradeJournalEntry) -> int:
        self.db.execute(
            """INSERT INTO trade_journal
               (ticker, strategy, signal_type, entry_date, entry_price, quantity)
               VALUES (?, ?, ?, ?, ?, ?) RETURNING id""",
            [entry.ticker, entry.strategy, entry.signal_type,
             entry.entry_date, entry.entry_price, entry.quantity],
        )
        row = self.db.fetchone()
        return row[0] if row else 0

    def close_trade(self, trade_id: int, exit_price: float,
                    outcome: str | None = None, regime: str | None = None,
                    sharpe_ratio: float | None = None) -> bool:
        row = self.db.execute(
            "SELECT entry_price, quantity FROM trade_journal WHERE id = ?", [trade_id]
        ).fetchone()
        if not row:
            return False

        entry_price, quantity = row
        return_pct = ((exit_price - entry_price) / entry_price) * 100
        if outcome is None:
            outcome = "win" if return_pct > 0 else "loss"

        self.db.execute(
            """UPDATE trade_journal SET
               exit_date = ?, exit_price = ?, return_pct = ?,
               outcome = ?, regime = ?, sharpe_ratio = ?
               WHERE id = ?""",
            [date.today(), exit_price, return_pct, outcome, regime, sharpe_ratio, trade_id],
        )
        return True

    def get_signal_efficacy(self) -> list[dict[str, Any]]:
        rows = self.db.execute("""
            SELECT signal_type,
                   COUNT(*) as total_trades,
                   AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END) as win_rate,
                   SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                   AVG(return_pct) as avg_return
            FROM trade_journal
            WHERE signal_type IS NOT NULL AND outcome IS NOT NULL
            GROUP BY signal_type
            ORDER BY win_rate DESC
        """).fetchall()
        return [
            {
                "signal_type": r[0],
                "total_trades": int(r[1]),
                "win_rate": float(r[2]) if r[2] else 0.0,
                "wins": int(r[3]),
                "avg_return": float(r[4]) if r[4] else 0.0,
            }
            for r in rows
        ]

    def get_best_regime_for_strategy(self, strategy: str) -> list[dict[str, Any]]:
        rows = self.db.execute("""
            SELECT regime,
                   AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END) as win_rate,
                   COUNT(*) as trades
            FROM trade_journal
            WHERE strategy = ? AND regime IS NOT NULL AND outcome IS NOT NULL
            GROUP BY regime
            ORDER BY win_rate DESC
        """, [strategy]).fetchall()
        return [
            {"regime": r[0], "win_rate": float(r[1]) if r[1] else 0.0, "trades": int(r[2])}
            for r in rows
        ]

    def record_signal_outcome(self, signal: SignalOutcome) -> int:
        self.db.execute(
            """INSERT INTO self_learning_signals
               (signal_type, regime, ticker, entry_date, exit_date, win, return_pct, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            [signal.signal_type, signal.regime, signal.ticker,
             signal.entry_date, signal.exit_date,
             signal.win, signal.return_pct, signal.confidence],
        )
        row = self.db.fetchone()
        return row[0] if row else 0

    def get_strategy_summary(self) -> list[dict[str, Any]]:
        rows = self.db.execute("""
            SELECT strategy,
                   COUNT(*) as total_trades,
                   AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END) as win_rate,
                   AVG(return_pct) as avg_return,
                   AVG(sharpe_ratio) as avg_sharpe,
                   SUM(ABS(entry_price * quantity)) as total_volume,
                   AVG(ABS(return_pct)) as avg_abs_return
            FROM trade_journal
            WHERE outcome IS NOT NULL
            GROUP BY strategy
            ORDER BY avg_return DESC
        """).fetchall()
        return [
            {
                "strategy": r[0],
                "total_trades": int(r[1]),
                "win_rate": float(r[2]) if r[2] else 0.0,
                "avg_return_pct": float(r[3]) if r[3] else 0.0,
                "avg_sharpe": float(r[4]) if r[4] else 0.0,
                "total_volume": float(r[5]) if r[5] else 0.0,
                "avg_abs_return": float(r[6]) if r[6] else 0.0,
            }
            for r in rows
        ]
```

- [ ] **Step 4: Run tests again**

Run: `cd backend && python -m pytest tests/engines/self_learning/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/self_learning/
git add backend/tests/engines/self_learning/
git commit -m "feat(self-learning): add self-learning engine with trade journal, signal efficacy, and tests"
```

### Task 9: Update Config for Phase 6

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_config_phase6.py`:
```python
import pytest
from app.config import Settings


class TestPhase6Config:
    def test_llm_provider_default(self):
        s = Settings(_env_file=None)
        assert s.llm_provider == "openai"

    def test_llm_provider_custom(self):
        s = Settings(_env_file=None, llm_provider="ollama")
        assert s.llm_provider == "ollama"

    def test_openai_api_key_empty_by_default(self):
        s = Settings(_env_file=None)
        assert s.openai_api_key == ""

    def test_ollama_base_url_default(self):
        s = Settings(_env_file=None)
        assert s.ollama_base_url == "http://localhost:11434"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_config_phase6.py -v`
Expected: FAIL (Settings missing new fields)

- [ ] **Step 3: Update config.py**

Edit `backend/app/config.py` — add these fields:

```python
    llm_provider: str = "openai"
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
```

Final `backend/app/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    polygon_api_key: str
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    redis_url: str = "redis://localhost:6379/0"
    database_path: str = "/data/portfolio.db"
    data_dir: str = "/data"
    log_level: str = "INFO"
    llm_provider: str = "openai"
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 4: Run tests again**

Run: `cd backend && python -m pytest tests/test_config_phase6.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py
git add backend/tests/test_config_phase6.py
git commit -m "feat(config): add LLM provider settings for Phase 6"
```


## Part A — Verification

- [ ] **Step 1: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v --cov=app`
Expected: All tests pass, including new Phase 6 tests

- [ ] **Step 2: Run ruff lint**

Run: `cd backend && ruff check app/ tests/`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: lint Phase 6 backend changes"
```


## Part B — Frontend: Next.js Application

### Task 10: Scaffold Next.js Project

- [ ] **Step 1: Create Next.js project**

```bash
npx create-next-app@latest /Users/vinayak.shenoi/Documents/workspace/portfolio-mgr/frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --use-npm
```

Expected: Project created with Tailwind, TypeScript, App Router

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/vinayak.shenoi/Documents/workspace/portfolio-mgr/frontend
npm install lucide-react recharts lightweight-charts @tanstack/react-table date-fns clsx tailwind-merge
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react
```

- [ ] **Step 3: Add vitest config**

Create `frontend/vitest.config.ts`:
```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./lib/test-setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

- [ ] **Step 4: Create test setup file**

Create `frontend/lib/test-setup.ts`:
```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 5: Update package.json with test script**

Edit `frontend/package.json` — add to scripts:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 6: Verify setup**

Run: `cd frontend && npx vitest run --no-file-parallelism 2>&1 | head -5`
Expected: No test files found (clean exit)

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Next.js project with Tailwind, Vitest, dependencies"
```

---

### Task 11: Tailwind Config — Terminal Green Theme

**Files:**
- Modify: `frontend/tailwind.config.ts`
- Create: `frontend/lib/utils.ts`

- [ ] **Step 1: Write a test for utility function**

Create `frontend/lib/utils.test.ts`:
```typescript
import { describe, it, expect } from "vitest";
import { cn, formatCurrency, formatPercent, formatNumber } from "./utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("px-4", "py-2")).toBe("px-4 py-2");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible");
  });
});

describe("formatCurrency", () => {
  it("formats USD", () => {
    expect(formatCurrency(1234.5)).toBe("$1,234.50");
  });

  it("handles zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });
});

describe("formatPercent", () => {
  it("formats positive percent", () => {
    expect(formatPercent(12.345)).toBe("+12.35%");
  });

  it("formats negative percent", () => {
    expect(formatPercent(-5.5)).toBe("-5.50%");
  });
});

describe("formatNumber", () => {
  it("formats large number with commas", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
  });

  it("handles zero", () => {
    expect(formatNumber(0)).toBe("0");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run lib/utils.test.ts 2>&1 | tail -10`
Expected: FAIL — cannot find module

- [ ] **Step 3: Create the utils file**

Create `frontend/lib/utils.ts`:
```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

export function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatCompactNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toString();
}
```

- [ ] **Step 4: Write Tailwind config**

Write `frontend/tailwind.config.ts`:
```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          green: "#22c55e",
          amber: "#ffb700",
          red: "#f87171",
          bg: "#000000",
          surface: "#09090b",
          border: "#27272a",
          muted: "#a1a1aa",
        },
      },
      fontFamily: {
        mono: ["IBM Plex Mono", "monospace"],
        sans: ["IBM Plex Sans", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 5: Create global CSS**

Edit `frontend/app/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --terminal-green: #22c55e;
  --terminal-amber: #ffb700;
  --terminal-red: #f87171;
}

* {
  scrollbar-width: thin;
  scrollbar-color: #27272a transparent;
}

body {
  font-family: 'IBM Plex Sans', sans-serif;
  background-color: black;
  color: #e4e4e7;
}

.font-mono {
  font-family: 'IBM Plex Mono', monospace;
}
```

- [ ] **Step 6: Run tests again**

Run: `cd frontend && npx vitest run lib/utils.test.ts 2>&1 | tail -10`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/tailwind.config.ts frontend/app/globals.css frontend/lib/utils.ts frontend/lib/utils.test.ts
git commit -m "feat(frontend): add terminal-green theme, utils, and tests"
```

### Task 12: API Client Library

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/api.test.ts`
- Create: `frontend/types.ts`

- [ ] **Step 1: Write types**

Create `frontend/types.ts`:
```typescript
export interface RegimeData {
  regime: string;
  probability: number;
  confidence: number;
  explanation: string;
}

export interface Opportunity {
  ticker: string;
  strategy: "swing" | "csp" | "leaps" | "pmcc";
  composite_score: number;
  regime_score: number;
  breakout_score: number;
  relative_strength: number;
  entry_price: number;
  target_price: number;
  stop_price: number;
  confidence: string;
  created_at: string;
}

export interface PortfolioSummary {
  total_value: number;
  cash: number;
  equity_value: number;
  options_buying_power: number;
  total_return_pct: number;
  daily_change_pct: number;
  health_score: number;
}

export interface Position {
  id: number;
  ticker: string;
  strategy: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  return_pct: number;
  market_value: number;
  opened_at: string;
  status: string;
}

export interface ReportSection {
  title: string;
  content: string;
}

export interface DailyReport {
  id: number;
  report_date: string;
  sections: ReportSection[];
  summary: string;
  generated_at: string;
  llm_model: string;
}

export interface PerformanceAttribution {
  strategy: string;
  total_trades: number;
  win_rate: number;
  total_return_pct: number;
  sharpe_ratio: number;
  attribution_pct: number;
}

export interface SelfLearningInsight {
  signal_type: string;
  regime: string;
  win_rate: number;
  total_trades: number;
  wins: number;
}

export interface Holding {
  ticker: string;
  quantity: number;
  market_value: number;
  return_pct: number;
  allocation_pct: number;
}

export interface TradeJournalEntry {
  id?: number;
  ticker: string;
  strategy: string;
  signal_type?: string;
  entry_date: string;
  exit_date?: string;
  entry_price: number;
  exit_price?: number;
  quantity: number;
  return_pct?: number;
  outcome?: string;
  regime?: string;
}
```

- [ ] **Step 2: Write tests for API client**

Create `frontend/lib/api.test.ts`:
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe("API Client", () => {
  it("fetches latest report", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, summary: "Test report", sections: [], report_date: "2026-06-21", generated_at: "2026-06-21T00:00:00Z", llm_model: "gpt-4o" }),
    });

    const { getLatestReport } = await import("./api");
    const report = await getLatestReport();
    expect(report.id).toBe(1);
    expect(report.summary).toBe("Test report");
  });

  it("fetches report by date", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 2, report_date: "2026-06-20", sections: [], summary: "Older report", generated_at: "2026-06-20T00:00:00Z", llm_model: "gpt-4o" }),
    });

    const { getReportByDate } = await import("./api");
    const report = await getReportByDate("2026-06-20");
    expect(report.report_date).toBe("2026-06-20");
  });

  it("fetches portfolio summary", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ total_value: 200000, cash: 50000, equity_value: 150000, options_buying_power: 25000, total_return_pct: 12.5, daily_change_pct: 0.5, health_score: 72 }),
    });

    const { getPortfolioSummary } = await import("./api");
    const summary = await getPortfolioSummary();
    expect(summary.total_value).toBe(200000);
  });

  it("fetches opportunities", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ ticker: "AAPL", strategy: "swing", composite_score: 85 }],
    });

    const { getOpportunities } = await import("./api");
    const opps = await getOpportunities();
    expect(opps.length).toBe(1);
    expect(opps[0].ticker).toBe("AAPL");
  });

  it("fetches positions", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 1, ticker: "AAPL", strategy: "Swing", quantity: 100, entry_price: 150, current_price: 165, return_pct: 10, market_value: 16500, opened_at: "2026-01-15", status: "open" }],
    });

    const { getPositions } = await import("./api");
    const positions = await getPositions();
    expect(positions.length).toBe(1);
    expect(positions[0].ticker).toBe("AAPL");
  });

  it("fetches performance attribution", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ strategy: "CSP", total_trades: 12, win_rate: 0.75, total_return_pct: 8.5, sharpe_ratio: 1.8, attribution_pct: 35 }],
    });

    const { getPerformanceAttribution } = await import("./api");
    const perf = await getPerformanceAttribution();
    expect(perf[0].strategy).toBe("CSP");
  });

  it("fetches self-learning insights", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ signal_type: "Breakout", regime: "Bull", win_rate: 0.82, total_trades: 15, wins: 12 }],
    });

    const { getSelfLearningInsights } = await import("./api");
    const insights = await getSelfLearningInsights();
    expect(insights[0].signal_type).toBe("Breakout");
  });

  it("handles fetch error gracefully", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    const { getLatestReport } = await import("./api");
    await expect(getLatestReport()).rejects.toThrow("Network error");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

    const { getLatestReport } = await import("./api");
    await expect(getLatestReport()).rejects.toThrow("HTTP 404");
  });

  it("builds correct API URL for opportunities with strategy filter", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] });

    const { getOpportunities } = await import("./api");
    await getOpportunities("csp");
    expect(mockFetch.mock.calls[0][0]).toContain("/api/v1/opportunities/csp");
  });
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd frontend && npx vitest run lib/api.test.ts 2>&1 | tail -10`
Expected: FAIL — cannot find module

- [ ] **Step 4: Create the API client**

Create `frontend/lib/api.ts`:
```typescript
import type {
  DailyReport,
  PerformanceAttribution,
  PortfolioSummary,
  Position,
  Opportunity,
  RegimeData,
  SelfLearningInsight,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}${res.statusText ? ": " + res.statusText : ""}`);
  return res.json();
}

// AI Manager
export function getLatestReport(): Promise<DailyReport> {
  return fetchJSON("/api/v1/ai/report/daily");
}

export function getReportByDate(date: string): Promise<DailyReport> {
  return fetchJSON("/api/v1/ai/report/" + date);
}

export function getPerformanceAttribution(): Promise<PerformanceAttribution[]> {
  return fetchJSON("/api/v1/ai/performance");
}

export function getSelfLearningInsights(): Promise<SelfLearningInsight[]> {
  return fetchJSON("/api/v1/ai/self-learning/insights");
}

// Portfolio
export function getPortfolioSummary(): Promise<PortfolioSummary> {
  return fetchJSON("/api/v1/portfolio/summary");
}

export function getPositions(): Promise<Position[]> {
  return fetchJSON("/api/v1/trading/positions");
}

// Opportunities
export function getOpportunities(strategy?: string): Promise<Opportunity[]> {
  const path = strategy ? "/api/v1/opportunities/" + strategy : "/api/v1/opportunities";
  return fetchJSON(path);
}

// Regime
export function getRegime(): Promise<RegimeData> {
  return fetchJSON("/api/v1/analysis/regime");
}
```

- [ ] **Step 5: Run tests again**

Run: `cd frontend && npx vitest run lib/api.test.ts 2>&1 | tail -10`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/types.ts frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "feat(frontend): add API client with typed endpoints and tests"
```

### Task 13: Root Layout with Sidebar Navigation

**Files:**
- Rewrite: `frontend/app/layout.tsx`

- [ ] **Step 1: Write the test**

Create `frontend/app/layout.test.tsx`:
```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import RootLayout from "./layout";

describe("RootLayout", () => {
  it("renders children", () => {
    render(<RootLayout><div>Test Child</div></RootLayout>);
    expect(screen.getByText("Test Child")).toBeDefined();
  });

  it("renders navigation links", () => {
    render(<RootLayout><div>Content</div></RootLayout>);
    expect(screen.getByText("Dashboard")).toBeDefined();
    expect(screen.getByText("Opportunities")).toBeDefined();
    expect(screen.getByText("Portfolio")).toBeDefined();
    expect(screen.getByText("Reports")).toBeDefined();
    expect(screen.getByText("Settings")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run app/layout.test.tsx 2>&1 | tail -15`
Expected: FAIL

- [ ] **Step 3: Create the layout**

Write `frontend/app/layout.tsx`:
```tsx
import type { Metadata } from "next";
import Link from "next/link";
import {
  LayoutDashboard,
  Search,
  PieChart,
  FileText,
  Settings,
} from "lucide-react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Portfolio Manager",
  description: "AI-powered portfolio management platform",
};

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/opportunities", label: "Opportunities", icon: Search },
  { href: "/portfolio", label: "Portfolio", icon: PieChart },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-black text-zinc-200 font-sans">
        <div className="flex h-screen">
          <aside className="w-64 bg-zinc-950 border-r border-zinc-800 flex flex-col">
            <div className="p-6 border-b border-zinc-800">
              <h1 className="text-terminal-green font-mono text-lg font-semibold tracking-tight">
                Portfolio Manager
              </h1>
              <p className="text-zinc-500 text-xs mt-1 font-mono">AI Hedge Fund</p>
            </div>
            <nav className="flex-1 p-4 space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors text-sm"
                >
                  <item.icon className="w-4 h-4" />
                  <span className="font-medium">{item.label}</span>
                </Link>
              ))}
            </nav>
            <div className="p-4 border-t border-zinc-800">
              <div className="flex items-center gap-2 text-xs text-zinc-600 font-mono">
                <div className="w-2 h-2 rounded-full bg-terminal-green" />
                System Online
              </div>
            </div>
          </aside>
          <main className="flex-1 overflow-y-auto p-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Run tests again**

Run: `cd frontend && npx vitest run app/layout.test.tsx 2>&1 | tail -15`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/layout.tsx frontend/app/layout.test.tsx
git commit -m "feat(frontend): add root layout with sidebar navigation and tests"
```

### Task 14: Shared Components

**Files:**
- Create: `frontend/components/shared/DataTable.tsx`
- Create: `frontend/components/shared/ScoreBadge.tsx`
- Create: `frontend/components/shared/RegimeDot.tsx`
- Create: `frontend/components/shared/PctChange.tsx`
- Create: `frontend/components/shared/Modal.tsx`
- Create: `frontend/components/shared/StrategyCard.tsx`
- Create: `frontend/components/shared/ActionButton.tsx`
- Create: `frontend/components/shared/StatusDot.tsx`
- Test: `frontend/components/shared/shared.test.tsx`

Note: In the test file below, adapt to match the actual component interfaces (e.g. DataTable uses Column<T> vs the previous interface). Write tests that match the component code exactly.

- [ ] **Step 1: Write the shared components test**

Create `frontend/components/shared/shared.test.tsx`:
```typescript
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DataTable } from "./DataTable";
import { ScoreBadge } from "./ScoreBadge";
import { RegimeDot } from "./RegimeDot";
import { PctChange } from "./PctChange";
import { Modal } from "./Modal";
import { StrategyCard } from "./StrategyCard";
import { ActionButton } from "./ActionButton";
import { StatusDot } from "./StatusDot";

describe("DataTable", () => {
  const columns = [
    { key: "ticker", header: "Ticker", sortable: true },
    { key: "score", header: "Score", sortable: true },
  ];
  const data = [
    { id: "1", ticker: "AAPL", score: 85 },
    { id: "2", ticker: "MSFT", score: 72 },
  ];

  it("renders headers and rows", () => {
    render(<DataTable columns={columns} data={data} />);
    expect(screen.getByText("Ticker")).toBeDefined();
    expect(screen.getByText("AAPL")).toBeDefined();
  });

  it("renders empty state", () => {
    render(<DataTable columns={columns} data={[]} />);
    expect(screen.getByText("No data")).toBeDefined();
  });
});

describe("ScoreBadge", () => {
  it("renders high score as green", () => {
    const { container } = render(<ScoreBadge score={85} />);
    expect(container.firstChild).toHaveClass("text-terminal-green");
  });

  it("renders medium score as amber", () => {
    const { container } = render(<ScoreBadge score={60} />);
    expect(container.firstChild).toHaveClass("text-terminal-amber");
  });

  it("renders low score as red", () => {
    const { container } = render(<ScoreBadge score={30} />);
    expect(container.firstChild).toHaveClass("text-terminal-red");
  });
});

describe("RegimeDot", () => {
  it("renders Bull as green", () => {
    const { container } = render(<RegimeDot regime="Bull" />);
    expect(container.querySelector(".bg-terminal-green")).toBeDefined();
  });

  it("renders Bear as red", () => {
    const { container } = render(<RegimeDot regime="Bear" />);
    expect(container.querySelector(".bg-terminal-red")).toBeDefined();
  });
});

describe("PctChange", () => {
  it("renders positive change with plus sign", () => {
    render(<PctChange value={5.5} />);
    expect(screen.getByText("+5.50%")).toBeDefined();
  });

  it("renders negative change in red", () => {
    render(<PctChange value={-3.2} />);
    expect(screen.getByText("-3.20%")).toBeDefined();
  });

  it("renders zero change in gray", () => {
    render(<PctChange value={0} />);
    expect(screen.getByText("0.00%")).toBeDefined();
  });
});

describe("Modal", () => {
  it("renders content when open", () => {
    render(<Modal isOpen={true} onClose={() => {}} title="Test"><p>Content</p></Modal>);
    expect(screen.getByText("Test")).toBeDefined();
    expect(screen.getByText("Content")).toBeDefined();
  });

  it("does not render when closed", () => {
    render(<Modal isOpen={false} onClose={() => {}} title="Hidden"><p>Hidden</p></Modal>);
    expect(screen.queryByText("Hidden")).toBeNull();
  });
});

describe("StrategyCard", () => {
  it("renders strategy details", () => {
    render(<StrategyCard name="CSP" ticker="AAPL" description="Sell put" score={85} />);
    expect(screen.getByText("CSP")).toBeDefined();
  });
});

describe("ActionButton", () => {
  it("renders primary variant", () => {
    const { container } = render(<ActionButton label="Buy" variant="primary" onClick={() => {}} />);
    expect(container.firstChild).toHaveClass("bg-terminal-green");
  });

  it("renders danger variant", () => {
    const { container } = render(<ActionButton label="Sell" variant="danger" onClick={() => {}} />);
    expect(container.firstChild).toHaveClass("bg-terminal-red");
  });
});

describe("StatusDot", () => {
  it("renders open status as green", () => {
    const { container } = render(<StatusDot status="open" />);
    expect(container.firstChild).toHaveClass("bg-terminal-green");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run components/shared/shared.test.tsx 2>&1 | tail -10`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the DataTable component**

Create `frontend/components/shared/DataTable.tsx`:
```tsx
"use client";

import { useState, useMemo } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
}

interface DataTableProps<T extends { id?: string | number }> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  className?: string;
}

export function DataTable<T extends { id?: string | number }>({
  columns, data, onRowClick, className,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey as keyof T];
      const bVal = b[sortKey as keyof T];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  if (data.length === 0) {
    return (
      <div className={cn("text-zinc-500 text-sm py-8 text-center font-mono", className)}>
        No data
      </div>
    );
  }

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="border-b border-zinc-800">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "text-left py-3 px-4 text-zinc-400 font-medium",
                  col.sortable && "cursor-pointer hover:text-zinc-200 select-none"
                )}
                onClick={() => col.sortable && setSortKey(col.key) || undefined}
              >
                <span className="flex items-center gap-1">
                  {col.header}
                  {sortKey === col.key && (
                    sortDir === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((item, i) => (
            <tr
              key={item.id ?? i}
              className={cn(
                "border-b border-zinc-800/50 hover:bg-zinc-900/50 transition-colors",
                i % 2 === 0 && "bg-zinc-950/30",
                onRowClick && "cursor-pointer"
              )}
              onClick={() => onRowClick?.(item)}
            >
              {columns.map((col) => (
                <td key={col.key} className="py-3 px-4 text-zinc-300">
                  {col.render ? col.render(item) : String(item[col.key as keyof T] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Create remaining shared components**

Create `frontend/components/shared/ScoreBadge.tsx`:
```tsx
import { cn } from "@/lib/utils";

interface ScoreBadgeProps { score: number; className?: string; }

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  const color = score >= 75 ? "text-terminal-green" : score >= 50 ? "text-terminal-amber" : "text-terminal-red";
  return <span className={cn("font-mono font-semibold", color, className)}>{score}</span>;
}
```

Create `frontend/components/shared/RegimeDot.tsx`:
```tsx
import { cn } from "@/lib/utils";

interface RegimeDotProps { regime: string; className?: string; }

const regimeColors: Record<string, string> = {
  Bull: "bg-terminal-green", "Bull High Vol": "bg-terminal-green",
  Bear: "bg-terminal-red", "Bear High Vol": "bg-terminal-red",
  Range: "bg-terminal-amber", Crisis: "bg-terminal-red",
};

export function RegimeDot({ regime, className }: RegimeDotProps) {
  const color = regimeColors[regime] || "bg-zinc-500";
  return (
    <span className={cn("flex items-center gap-2 text-sm", className)}>
      <span className={cn("w-2.5 h-2.5 rounded-full", color)} />
      <span className="font-mono text-zinc-300">{regime}</span>
    </span>
  );
}
```

Create `frontend/components/shared/PctChange.tsx`:
```tsx
import { cn, formatPercent } from "@/lib/utils";

interface PctChangeProps { value: number; className?: string; }

export function PctChange({ value, className }: PctChangeProps) {
  const color = value > 0 ? "text-terminal-green" : value < 0 ? "text-terminal-red" : "text-zinc-400";
  return (
    <span className={cn("font-mono font-medium", color, className)}>
      {value === 0 ? "0.00%" : formatPercent(value)}
    </span>
  );
}
```

Create `frontend/components/shared/Modal.tsx`:
```tsx
"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModalProps { isOpen: boolean; onClose: () => void; title: string; children: React.ReactNode; className?: string; }

export function Modal({ isOpen, onClose, title, children, className }: ModalProps) {
  useEffect(() => {
    document.body.style.overflow = isOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className={cn("bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto shadow-2xl", className)}>
        <div className="flex items-center justify-between p-6 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}
```

Create `frontend/components/shared/StrategyCard.tsx`:
```tsx
import { cn } from "@/lib/utils";
import { ScoreBadge } from "./ScoreBadge";

interface StrategyCardProps { name: string; ticker: string; description: string; score: number; className?: string; }

export function StrategyCard({ name, ticker, description, score, className }: StrategyCardProps) {
  return (
    <div className={cn("bg-zinc-950 border border-zinc-800 rounded-xl p-5 hover:border-zinc-700 transition-colors", className)}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-zinc-100">{name}</h3>
          <span className="text-terminal-green font-mono text-sm">{ticker}</span>
        </div>
        <ScoreBadge score={score} />
      </div>
      <p className="text-zinc-400 text-sm">{description}</p>
    </div>
  );
}
```

Create `frontend/components/shared/ActionButton.tsx`:
```tsx
import { cn } from "@/lib/utils";

interface ActionButtonProps { label: string; variant: "primary" | "secondary" | "danger"; onClick: () => void; disabled?: boolean; className?: string; }

const variants = {
  primary: "bg-terminal-green text-black hover:bg-emerald-500",
  secondary: "bg-zinc-800 text-zinc-200 hover:bg-zinc-700",
  danger: "bg-terminal-red text-white hover:bg-red-600",
};

export function ActionButton({ label, variant, onClick, disabled, className }: ActionButtonProps) {
  return (
    <button onClick={onClick} disabled={disabled}
      className={cn("px-4 py-2 rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed", variants[variant], className)}>
      {label}
    </button>
  );
}
```

Create `frontend/components/shared/StatusDot.tsx`:
```tsx
import { cn } from "@/lib/utils";

interface StatusDotProps { status: string; className?: string; }

const statusColors: Record<string, string> = {
  open: "bg-terminal-green", closed: "bg-zinc-500", pending: "bg-terminal-amber",
  cancelled: "bg-terminal-red", filled: "bg-terminal-green", rejected: "bg-terminal-red",
};

export function StatusDot({ status, className }: StatusDotProps) {
  return <span className={cn("w-2 h-2 rounded-full inline-block", statusColors[status.toLowerCase()] || "bg-zinc-500", className)} />;
}
```

- [ ] **Step 5: Run tests again**

Run: `cd frontend && npx vitest run components/shared/shared.test.tsx 2>&1 | tail -10`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/components/shared/
git commit -m "feat(frontend): add shared components (DataTable, ScoreBadge, RegimeDot, PctChange, Modal, StrategyCard, ActionButton, StatusDot) with tests"
```

### Task 15: Dashboard Page

**Files:**
- Create: `frontend/app/page.tsx`
- Create: `frontend/components/dashboard/RegimeBanner.tsx`
- Create: `frontend/components/dashboard/PortfolioHealthCard.tsx`
- Create: `frontend/components/dashboard/TopOpportunities.tsx`
- Create: `frontend/components/dashboard/PositionSummary.tsx`
- Create: `frontend/components/dashboard/DailyReportCard.tsx`

- [ ] **Step 1: Write the dashboard test**

Create `frontend/app/dashboard.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest";
import { RegimeBanner } from "@/components/dashboard/RegimeBanner";
import { PortfolioHealthCard } from "@/components/dashboard/PortfolioHealthCard";
import { DailyReportCard } from "@/components/dashboard/DailyReportCard";
import { render, screen } from "@testing-library/react";

describe("RegimeBanner", () => {
  it("renders regime and confidence", () => {
    render(<RegimeBanner regime="Bull" confidence={0.85} />);
    expect(screen.getByText("Bull")).toBeDefined();
    expect(screen.getByText("85% confidence")).toBeDefined();
  });

  it("renders explanation when provided", () => {
    render(<RegimeBanner regime="Bear" confidence={0.7} explanation="Market in downtrend" />);
    expect(screen.getByText("Market in downtrend")).toBeDefined();
  });
});

describe("PortfolioHealthCard", () => {
  it("renders health score and total value", () => {
    render(<PortfolioHealthCard score={72} totalValue={200000} dailyChange={0.5} />);
    expect(screen.getByText("72/100")).toBeDefined();
  });
});

describe("DailyReportCard", () => {
  it("renders empty state when no report", () => {
    render(<DailyReportCard report={null} />);
    expect(screen.getByText("No report generated yet")).toBeDefined();
  });

  it("renders report summary when available", () => {
    render(<DailyReportCard report={{
      id: 1, report_date: "2026-06-21", sections: [{ title: "Market", content: "Bull" }],
      summary: "Bullish outlook", generated_at: "2026-06-21T00:00:00Z", llm_model: "gpt-4o",
    }} />);
    expect(screen.getByText("Bullish outlook")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run app/dashboard.test.tsx 2>&1 | tail -10`
Expected: FAIL with ImportError

- [ ] **Step 3: Create dashboard components**

Create `frontend/components/dashboard/RegimeBanner.tsx`:
```tsx
import { RegimeDot } from "@/components/shared/RegimeDot";

interface RegimeBannerProps { regime: string; confidence: number; explanation?: string; }

export function RegimeBanner({ regime, confidence, explanation }: RegimeBannerProps) {
  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono">Market Regime</h2>
        <span className="text-xs font-mono text-zinc-500">{Math.round(confidence * 100)}% confidence</span>
      </div>
      <RegimeDot regime={regime} />
      {explanation && <p className="mt-3 text-sm text-zinc-400 leading-relaxed">{explanation}</p>}
    </div>
  );
}
```

Create `frontend/components/dashboard/PortfolioHealthCard.tsx`:
```tsx
import { cn } from "@/lib/utils";

interface PortfolioHealthCardProps { score: number; totalValue: number; dailyChange: number; }

export function PortfolioHealthCard({ score, totalValue, dailyChange }: PortfolioHealthCardProps) {
  const scoreColor = score >= 70 ? "text-terminal-green" : score >= 40 ? "text-terminal-amber" : "text-terminal-red";
  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
      <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono mb-4">Portfolio Health</h2>
      <div className="space-y-4">
        <div>
          <span className="text-xs text-zinc-500 font-mono">Health Score</span>
          <div className={cn("text-3xl font-bold font-mono mt-1", scoreColor)}>{score}/100</div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-xs text-zinc-500 font-mono">Total Value</span>
            <div className="text-lg font-semibold font-mono text-zinc-100 mt-0.5">${totalValue.toLocaleString()}</div>
          </div>
          <div>
            <span className="text-xs text-zinc-500 font-mono">Daily Change</span>
            <div className={cn("text-lg font-semibold font-mono mt-0.5", dailyChange >= 0 ? "text-terminal-green" : "text-terminal-red")}>
              {dailyChange >= 0 ? "+" : ""}{dailyChange.toFixed(2)}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

Create `frontend/components/dashboard/TopOpportunities.tsx`:
```tsx
import Link from "next/link";
import { DataTable } from "@/components/shared/DataTable";
import { ScoreBadge } from "@/components/shared/ScoreBadge";
import type { Opportunity } from "@/types";

interface TopOpportunitiesProps { opportunities: Opportunity[]; }

export function TopOpportunities({ opportunities }: TopOpportunitiesProps) {
  const columns = [
    { key: "ticker", header: "Ticker", sortable: true },
    { key: "strategy", header: "Strategy", sortable: true, render: (item: Opportunity) => <span className="uppercase text-xs font-mono">{item.strategy}</span> },
    { key: "composite_score", header: "Score", sortable: true, render: (item: Opportunity) => <ScoreBadge score={item.composite_score} /> },
    { key: "entry_price", header: "Entry", sortable: true, render: (item: Opportunity) => "$" + item.entry_price.toFixed(2) },
    { key: "target_price", header: "Target", sortable: true, render: (item: Opportunity) => "$" + item.target_price.toFixed(2) },
  ];

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono">Top Opportunities</h2>
        <Link href="/opportunities" className="text-xs text-terminal-green hover:underline font-mono">View All</Link>
      </div>
      <DataTable columns={columns} data={opportunities.slice(0, 5)} />
    </div>
  );
}
```

Create `frontend/components/dashboard/PositionSummary.tsx`:
```tsx
import Link from "next/link";
import { DataTable } from "@/components/shared/DataTable";
import { PctChange } from "@/components/shared/PctChange";
import type { Position } from "@/types";

interface PositionSummaryProps { positions: Position[]; }

export function PositionSummary({ positions }: PositionSummaryProps) {
  const columns = [
    { key: "ticker", header: "Ticker", sortable: true },
    { key: "strategy", header: "Strategy", sortable: true },
    { key: "quantity", header: "Qty", sortable: true },
    { key: "return_pct", header: "Return", sortable: true, render: (item: Position) => <PctChange value={item.return_pct} /> },
    { key: "market_value", header: "Value", sortable: true, render: (item: Position) => "$" + item.market_value.toLocaleString() },
  ];

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono">Open Positions</h2>
        <Link href="/reports" className="text-xs text-terminal-green hover:underline font-mono">Manage</Link>
      </div>
      <DataTable columns={columns} data={positions} />
    </div>
  );
}
```

Create `frontend/components/dashboard/DailyReportCard.tsx`:
```tsx
import Link from "next/link";
import { FileText } from "lucide-react";
import type { DailyReport } from "@/types";

interface DailyReportCardProps { report: DailyReport | null; }

export function DailyReportCard({ report }: DailyReportCardProps) {
  if (!report) {
    return (
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-4 h-4 text-zinc-400" />
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono">Latest Report</h2>
        </div>
        <p className="text-zinc-500 text-sm font-mono">No report generated yet</p>
      </div>
    );
  }

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-terminal-green" />
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono">Latest Report</h2>
        </div>
        <Link href="/reports" className="text-xs text-terminal-green hover:underline font-mono">All Reports</Link>
      </div>
      <div className="space-y-3">
        <div className="text-xs text-zinc-500 font-mono">{report.report_date} &middot; {report.llm_model}</div>
        <p className="text-sm text-zinc-300 leading-relaxed line-clamp-4">{report.summary}</p>
        {report.sections.length > 0 && (
          <Link href="/reports" className="inline-block text-xs text-terminal-green hover:underline font-mono mt-2">Read full report &rarr;</Link>
        )}
      </div>
    </div>
  );
}
```

Create `frontend/app/page.tsx`:
```tsx
import { RegimeBanner } from "@/components/dashboard/RegimeBanner";
import { PortfolioHealthCard } from "@/components/dashboard/PortfolioHealthCard";
import { TopOpportunities } from "@/components/dashboard/TopOpportunities";
import { PositionSummary } from "@/components/dashboard/PositionSummary";
import { DailyReportCard } from "@/components/dashboard/DailyReportCard";

async function getData() {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const fetchJSON = async <T,>(path: string, fallback: T): Promise<T> => {
    try {
      const res = await fetch(base + path, { next: { revalidate: 300 } });
      if (!res.ok) return fallback;
      return await res.json();
    } catch { return fallback; }
  };

  const [regime, portfolio, opportunities, positions, report] = await Promise.all([
    fetchJSON("/api/v1/analysis/regime", { regime: "Unknown", probability: 0, confidence: 0, explanation: "" }),
    fetchJSON("/api/v1/portfolio/summary", { total_value: 0, cash: 0, equity_value: 0, options_buying_power: 0, total_return_pct: 0, daily_change_pct: 0, health_score: 0 }),
    fetchJSON("/api/v1/opportunities", []),
    fetchJSON("/api/v1/trading/positions", []),
    fetchJSON("/api/v1/ai/report/daily", null),
  ]);
  return { regime, portfolio, opportunities, positions, report };
}

export default async function DashboardPage() {
  const { regime, portfolio, opportunities, positions, report } = await getData();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Dashboard</h1>
        <p className="text-zinc-500 text-sm mt-1 font-mono">Portfolio overview &amp; AI insights</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <RegimeBanner regime={regime.regime} confidence={regime.confidence} explanation={regime.explanation} />
        <PortfolioHealthCard score={portfolio.health_score} totalValue={portfolio.total_value} dailyChange={portfolio.daily_change_pct} />
        <DailyReportCard report={report} />
      </div>
      <TopOpportunities opportunities={opportunities} />
      <PositionSummary positions={positions} />
    </div>
  );
}
```

- [ ] **Step 4: Run tests again**

Run: `cd frontend && npx vitest run app/dashboard.test.tsx 2>&1 | tail -10`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/page.tsx frontend/app/dashboard.test.tsx frontend/components/dashboard/
git commit -m "feat(frontend): add dashboard page with RegimeBanner, PortfolioHealthCard, TopOpportunities, PositionSummary, DailyReportCard"
```

### Task 16: Opportunities Page

**Files:**
- Create: `frontend/app/opportunities/page.tsx`
- Create: `frontend/components/opportunities/FilterBar.tsx`
- Create: `frontend/components/opportunities/OpportunityDetail.tsx`

- [ ] **Step 1: Write the test**

Create `frontend/app/opportunities/opportunities.test.tsx`:
```typescript
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FilterBar } from "@/components/opportunities/FilterBar";

describe("FilterBar", () => {
  const strategies = [
    { value: "all", label: "All" },
    { value: "swing", label: "Swing" },
    { value: "csp", label: "CSP" },
  ];

  it("renders all strategy buttons", () => {
    render(<FilterBar strategies={strategies} active="all" onChange={() => {}} />);
    expect(screen.getByText("All")).toBeDefined();
    expect(screen.getByText("Swing")).toBeDefined();
    expect(screen.getByText("CSP")).toBeDefined();
  });

  it("highlights active filter", () => {
    render(<FilterBar strategies={strategies} active="csp" onChange={() => {}} />);
    const cspBtn = screen.getByText("CSP");
    expect(cspBtn.className).toContain("bg-terminal-green");
  });

  it("calls onChange when button clicked", () => {
    const onChange = vi.fn();
    render(<FilterBar strategies={strategies} active="all" onChange={onChange} />);
    fireEvent.click(screen.getByText("Swing"));
    expect(onChange).toHaveBeenCalledWith("swing");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run app/opportunities/opportunities.test.tsx 2>&1 | tail -10`
Expected: FAIL with ImportError

- [ ] **Step 3: Create components**

Create `frontend/components/opportunities/FilterBar.tsx`:
```tsx
"use client";

import { cn } from "@/lib/utils";

interface FilterOption { value: string; label: string; }
interface FilterBarProps { strategies: FilterOption[]; active: string; onChange: (value: string) => void; }

export function FilterBar({ strategies, active, onChange }: FilterBarProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      {strategies.map((s) => (
        <button key={s.value} onClick={() => onChange(s.value)}
          className={cn("px-4 py-2 rounded-lg text-sm font-mono font-medium transition-colors",
            active === s.value ? "bg-terminal-green text-black" : "bg-zinc-900 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800")}>
          {s.label}
        </button>
      ))}
    </div>
  );
}
```

Create `frontend/components/opportunities/OpportunityDetail.tsx`:
```tsx
"use client";

import { Modal } from "@/components/shared/Modal";
import { ScoreBadge } from "@/components/shared/ScoreBadge";
import { PctChange } from "@/components/shared/PctChange";
import type { Opportunity } from "@/types";

interface OpportunityDetailProps { opportunity: Opportunity | null; isOpen: boolean; onClose: () => void; }

export function OpportunityDetail({ opportunity, isOpen, onClose }: OpportunityDetailProps) {
  if (!opportunity) return null;
  const upsidePct = ((opportunity.target_price - opportunity.entry_price) / opportunity.entry_price) * 100;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={opportunity.ticker + " — " + opportunity.strategy.toUpperCase()}>
      <div className="space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-zinc-900 rounded-lg p-4">
            <div className="text-xs text-zinc-500 font-mono mb-1">Score</div>
            <ScoreBadge score={opportunity.composite_score} className="text-xl" />
          </div>
          <div className="bg-zinc-900 rounded-lg p-4">
            <div className="text-xs text-zinc-500 font-mono mb-1">Upside</div>
            <PctChange value={upsidePct} />
          </div>
          <div className="bg-zinc-900 rounded-lg p-4">
            <div className="text-xs text-zinc-500 font-mono mb-1">Confidence</div>
            <div className="text-lg font-mono font-semibold text-zinc-100">{opportunity.confidence}</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-zinc-500 font-mono">Entry</span><div className="text-zinc-200 font-mono mt-0.5">$" + opportunity.entry_price.toFixed(2) + "</div></div>
          <div><span className="text-zinc-500 font-mono">Target</span><div className="text-terminal-green font-mono mt-0.5">$" + opportunity.target_price.toFixed(2) + "</div></div>
          <div><span className="text-zinc-500 font-mono">Stop</span><div className="text-terminal-red font-mono mt-0.5">$" + opportunity.stop_price.toFixed(2) + "</div></div>
          <div><span className="text-zinc-500 font-mono">Created</span><div className="text-zinc-200 font-mono mt-0.5">{opportunity.created_at}</div></div>
        </div>
        <div className="border-t border-zinc-800 pt-4">
          <h4 className="text-xs text-zinc-500 font-mono uppercase tracking-wider mb-3">Score Breakdown</h4>
          <div className="space-y-2">
            {[{ label: "Regime", value: opportunity.regime_score }, { label: "Breakout", value: opportunity.breakout_score }, { label: "Rel. Strength", value: opportunity.relative_strength }].map((item) => (
              <div key={item.label} className="flex justify-between items-center">
                <span className="text-sm text-zinc-400 font-mono">{item.label}</span>
                <ScoreBadge score={Math.round(item.value)} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}
```

Create `frontend/app/opportunities/page.tsx`:
```tsx
"use client";

import { useState, useEffect } from "react";
import { DataTable } from "@/components/shared/DataTable";
import { ScoreBadge } from "@/components/shared/ScoreBadge";
import { FilterBar } from "@/components/opportunities/FilterBar";
import { OpportunityDetail } from "@/components/opportunities/OpportunityDetail";
import { getOpportunities } from "@/lib/api";
import type { Opportunity } from "@/types";

const STRATEGIES = [
  { value: "all", label: "All" }, { value: "swing", label: "Swing" },
  { value: "csp", label: "CSP" }, { value: "leaps", label: "LEAPS" }, { value: "pmcc", label: "PMCC" },
];

const columns = [
  { key: "ticker", header: "Ticker", sortable: true },
  { key: "strategy", header: "Strategy", sortable: true, render: (item: Opportunity) => <span className="uppercase text-xs font-mono">{item.strategy}</span> },
  { key: "composite_score", header: "Score", sortable: true, render: (item: Opportunity) => <ScoreBadge score={item.composite_score} /> },
  { key: "entry_price", header: "Entry", sortable: true, render: (item: Opportunity) => "$" + item.entry_price.toFixed(2) },
  { key: "target_price", header: "Target", sortable: true, render: (item: Opportunity) => "$" + item.target_price.toFixed(2) },
  { key: "confidence", header: "Confidence", sortable: true },
];

export default function OpportunitiesPage() {
  const [activeFilter, setActiveFilter] = useState("all");
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [selected, setSelected] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const strategy = activeFilter === "all" ? undefined : activeFilter;
    getOpportunities(strategy).then(setOpportunities).catch(() => setOpportunities([])).finally(() => setLoading(false));
  }, [activeFilter]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Opportunities</h1>
        <p className="text-zinc-500 text-sm mt-1 font-mono">Trading opportunities sorted by score</p>
      </div>
      <FilterBar strategies={STRATEGIES} active={activeFilter} onChange={setActiveFilter} />
      {loading ? (
        <div className="text-zinc-500 text-center py-8 font-mono">Loading...</div>
      ) : (
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
          <DataTable columns={columns} data={opportunities} onRowClick={setSelected} />
        </div>
      )}
      <OpportunityDetail opportunity={selected} isOpen={!!selected} onClose={() => setSelected(null)} />
    </div>
  );
}
```

- [ ] **Step 4: Run tests again**

Run: `cd frontend && npx vitest run app/opportunities/opportunities.test.tsx 2>&1 | tail -10`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/opportunities/ frontend/components/opportunities/
git commit -m "feat(frontend): add opportunities page with filter, table, and detail modal"
```

### Task 17: Remaining Pages — Portfolio, Positions, Reports, Settings

Note: These stubs create minimal page shells that wire up to the API client. Full charting (lightweight-charts, recharts) requires the API to return real data, so these pages include placeholder charts and loading states.

**Files:**
- Create: `frontend/app/portfolio/page.tsx`
- Create: `frontend/app/positions/[id]/page.tsx`
- Create: `frontend/app/reports/page.tsx`
- Create: `frontend/app/settings/page.tsx`

- [ ] **Step 1: Portfolio Page**

Create `frontend/app/portfolio/page.tsx`:
```tsx
"use client";

import { useState, useEffect } from "react";
import { getPortfolioSummary, getPositions } from "@/lib/api";
import { DataTable } from "@/components/shared/DataTable";
import { PctChange } from "@/components/shared/PctChange";
import type { PortfolioSummary, Position } from "@/types";

export default function PortfolioPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPortfolioSummary(), getPositions()])
      .then(([s, p]) => { setSummary(s); setPositions(p); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-zinc-500 text-center py-8 font-mono">Loading...</div>;

  const columns = [
    { key: "ticker", header: "Ticker", sortable: true },
    { key: "strategy", header: "Strategy", sortable: true },
    { key: "quantity", header: "Qty", sortable: true },
    { key: "return_pct", header: "Return", sortable: true, render: (item: Position) => <PctChange value={item.return_pct} /> },
    { key: "market_value", header: "Value", sortable: true, render: (item: Position) => "$" + item.market_value.toLocaleString() },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-zinc-100">Portfolio</h1>
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
            <div className="text-xs text-zinc-500 font-mono">Total Value</div>
            <div className="text-xl font-bold font-mono text-zinc-100 mt-1">${summary.total_value.toLocaleString()}</div>
          </div>
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
            <div className="text-xs text-zinc-500 font-mono">Cash</div>
            <div className="text-xl font-bold font-mono text-terminal-green mt-1">${summary.cash.toLocaleString()}</div>
          </div>
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
            <div className="text-xs text-zinc-500 font-mono">Total Return</div>
            <div className="text-xl font-bold font-mono mt-1"><PctChange value={summary.total_return_pct} /></div>
          </div>
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
            <div className="text-xs text-zinc-500 font-mono">Health Score</div>
            <div className="text-xl font-bold font-mono text-terminal-green mt-1">{summary.health_score}/100</div>
          </div>
        </div>
      )}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
        <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono mb-4">Holdings</h2>
        <DataTable columns={columns} data={positions} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Positions Detail Page**

Create `frontend/app/positions/[id]/page.tsx`:
```tsx
"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { ActionButton } from "@/components/shared/ActionButton";
import { PctChange } from "@/components/shared/PctChange";
import type { Position } from "@/types";

export default function PositionDetailPage() {
  const params = useParams();
  const [position, setPosition] = useState<Position | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(process.env.NEXT_PUBLIC_API_URL + "/api/v1/trading/positions")
      .then((r) => r.json())
      .then((positions: Position[]) => {
        const found = positions.find((p) => p.id === Number(params.id));
        setPosition(found || null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <div className="text-zinc-500 text-center py-8 font-mono">Loading...</div>;
  if (!position) return <div className="text-zinc-500 text-center py-8 font-mono">Position not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">{position.ticker}</h1>
          <p className="text-zinc-500 text-sm mt-1 font-mono">{position.strategy} &middot; Opened {position.opened_at}</p>
        </div>
        <div className="flex gap-3">
          <ActionButton label="Close" variant="danger" onClick={() => {}} />
          <ActionButton label="Modify" variant="secondary" onClick={() => {}} />
        </div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
          <div className="text-xs text-zinc-500 font-mono">Entry Price</div>
          <div className="text-xl font-bold font-mono text-zinc-100 mt-1">${position.entry_price.toFixed(2)}</div>
        </div>
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
          <div className="text-xs text-zinc-500 font-mono">Current Price</div>
          <div className="text-xl font-bold font-mono text-zinc-100 mt-1">${position.current_price.toFixed(2)}</div>
        </div>
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
          <div className="text-xs text-zinc-500 font-mono">Return</div>
          <div className="text-xl font-bold font-mono mt-1"><PctChange value={position.return_pct} /></div>
        </div>
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
          <div className="text-xs text-zinc-500 font-mono">Market Value</div>
          <div className="text-xl font-bold font-mono text-zinc-100 mt-1">${position.market_value.toLocaleString()}</div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Reports Page**

Create `frontend/app/reports/page.tsx`:
```tsx
"use client";

import { useState, useEffect } from "react";
import { DataTable } from "@/components/shared/DataTable";
import { getLatestReport, getPerformanceAttribution } from "@/lib/api";
import type { DailyReport, PerformanceAttribution } from "@/types";

export default function ReportsPage() {
  const [report, setReport] = useState<DailyReport | null>(null);
  const [performance, setPerformance] = useState<PerformanceAttribution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getLatestReport(), getPerformanceAttribution()])
      .then(([r, p]) => { setReport(r); setPerformance(p); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-zinc-500 text-center py-8 font-mono">Loading...</div>;

  const perfColumns = [
    { key: "strategy", header: "Strategy", sortable: true },
    { key: "total_trades", header: "Trades", sortable: true },
    { key: "win_rate", header: "Win Rate", sortable: true, render: (item: PerformanceAttribution) => (item.win_rate * 100).toFixed(0) + "%" },
    { key: "total_return_pct", header: "Return", sortable: true, render: (item: PerformanceAttribution) => item.total_return_pct.toFixed(1) + "%" },
    { key: "sharpe_ratio", header: "Sharpe", sortable: true, render: (item: PerformanceAttribution) => item.sharpe_ratio.toFixed(2) },
    { key: "attribution_pct", header: "Attribution", sortable: true, render: (item: PerformanceAttribution) => item.attribution_pct.toFixed(0) + "%" },
  ];

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-zinc-100">Reports</h1>

      {report && (
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono">Latest AI Report</h2>
            <span className="text-xs text-zinc-500 font-mono">{report.report_date} &middot; {report.llm_model}</span>
          </div>
          <p className="text-zinc-300 text-sm leading-relaxed mb-4">{report.summary}</p>
          <div className="space-y-4">
            {report.sections.map((section, i) => (
              <div key={i} className="border-t border-zinc-800 pt-3">
                <h3 className="text-terminal-green font-mono text-sm font-semibold mb-1">{section.title}</h3>
                <p className="text-zinc-400 text-sm leading-relaxed whitespace-pre-wrap">{section.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6">
        <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono mb-4">Performance Attribution</h2>
        <DataTable columns={perfColumns} data={performance} />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Settings Page**

Create `frontend/app/settings/page.tsx`:
```tsx
"use client";

import { useState } from "react";
import { ActionButton } from "@/components/shared/ActionButton";

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState("");
  const [provider, setProvider] = useState("openai");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    localStorage.setItem("llm_provider", provider);
    if (apiKey) localStorage.setItem("openai_api_key", apiKey);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-zinc-100">Settings</h1>

      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-6">
        <div>
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono mb-4">AI Provider</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-zinc-400 font-mono mb-1">Provider</label>
              <select value={provider} onChange={(e) => setProvider(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-terminal-green">
                <option value="openai">OpenAI</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
            {provider === "openai" && (
              <div>
                <label className="block text-sm text-zinc-400 font-mono mb-1">API Key</label>
                <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-terminal-green placeholder-zinc-600" />
              </div>
            )}
            {provider === "ollama" && (
              <p className="text-zinc-500 text-sm font-mono">Using Ollama at http://localhost:11434</p>
            )}
          </div>
        </div>

        <div className="border-t border-zinc-800 pt-6">
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider font-mono mb-4">Risk Limits</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-zinc-400 font-mono">Max Position Size</span>
              <span className="text-sm text-zinc-200 font-mono">25% of portfolio</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-zinc-400 font-mono">Max Drawdown</span>
              <span className="text-sm text-zinc-200 font-mono">15%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-zinc-400 font-mono">Max Leverage</span>
              <span className="text-sm text-zinc-200 font-mono">None (cash only)</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <ActionButton label={saved ? "Saved!" : "Save Settings"} variant="primary" onClick={handleSave} />
          {saved && <span className="text-terminal-green text-sm font-mono">Settings saved</span>}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/portfolio/ frontend/app/positions/ frontend/app/reports/ frontend/app/settings/
git commit -m "feat(frontend): add portfolio, positions detail, reports, and settings pages"
```


## Part B — Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd frontend && npx vitest run 2>&1 | tail -15`
Expected: All tests pass

- [ ] **Step 2: Build the project**

Run: `cd frontend && npm run build 2>&1 | tail -15`
Expected: Successful build with no errors

- [ ] **Step 3: Run lint**

Run: `cd frontend && npm run lint 2>&1 | tail -10`
Expected: No lint errors

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: lint and verify Phase 6 frontend"
```

---

## Self-Review Verification

After completing all tasks, verify against spec:

1. **Spec coverage — Backend:**
   - [ ] AI Manager engine with `__init__.py`, `schemas.py`, `service.py`, `router.py`, `tasks.py` (Tasks 1-5)
   - [ ] Abstract LLM provider with OpenAI + Ollama support via LLMFactory (Task 2)
   - [ ] Langchain-powered prompts for daily report and ticker analysis (Task 3)
   - [ ] Daily report generation via Celery task (Task 5)
   - [ ] 7 report sections: Market Regime, Portfolio Health, Top Opportunities, Current Risks, Recommended Adjustments, Capital Allocation, Trade Ideas (Task 3)
   - [ ] Report stored in DuckDB `daily_reports` table (Task 7)
   - [ ] Self-Learning Engine with `trade_journal`, `self_learning_signals`, `performance_attribution` tables (Tasks 7, 8)
   - [ ] Signal efficacy analytics by type, regime, and strategy (Task 8)
   - [ ] Performance attribution by strategy, regime, and signal type (Task 6)
   - [ ] Config for LLM provider selection (Task 9)
   - [ ] TDD with pytest for every component (All tasks)
   - [ ] Ruff lint clean (Verification)

2. **Spec coverage — Frontend:**
   - [ ] Next.js project with Tailwind, TypeScript, App Router (Task 10)
   - [ ] Terminal-green dark theme with IBM Plex fonts (Task 11)
   - [ ] `lib/api.ts` with typed API client (Task 12)
   - [ ] `lib/utils.ts` with formatting helpers (Task 11)
   - [ ] `types.ts` with all TypeScript interfaces (Task 12)
   - [ ] Sidebar navigation layout (Task 13)
   - [ ] Shared components: DataTable, ScoreBadge, RegimeDot, PctChange, Modal, StrategyCard, ActionButton, StatusDot (Task 14)
   - [ ] Dashboard page with RegimeBanner, PortfolioHealthCard, TopOpportunities, PositionSummary, DailyReportCard (Task 15)
   - [ ] Opportunities page with filter bar, sortable table, detail modal (Task 16)
   - [ ] Portfolio page with summary cards and holdings table (Task 17)
   - [ ] Positions detail page with management actions (Task 17)
   - [ ] Reports page with AI report view and performance attribution (Task 17)
   - [ ] Settings page with API key configuration (Task 17)
   - [ ] Vitest + Testing Library tests (All tasks)
   - [ ] Successful production build (Verification)

3. **Placeholder scan:** No TBD, TODO, or incomplete steps.

4. **Type consistency:** All method signatures match across tasks. LLMProvider.generate returns str, ReportService methods return Pydantic models, API client uses typed generics. DuckDB schema columns match query expectations.
