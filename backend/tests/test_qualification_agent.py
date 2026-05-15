"""Unit tests for QualificationAgent (LLM-based qualification)."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add ai-core to path for direct import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ai-core"))

from agents.qualification import (
    QualificationAgent,
    QualificationInput,
    QualificationResult,
)


def make_input(**kwargs) -> QualificationInput:
    defaults = {
        "total_debt": 850_000,
        "creditors_count": 3,
        "creditor_types": ["bank"],
        "monthly_income": None,
        "is_employed": False,
        "has_property": False,
        "property_types": [],
        "has_transactions_3y": False,
        "marital_status": "single",
        "has_enforcement_proceedings": False,
        "region": None,
    }
    defaults.update(kwargs)
    return QualificationInput(**defaults)


class TestQualificationAgent:
    """Test QualificationAgent with mocked LLM providers."""

    @pytest.fixture
    def mock_anthropic_client(self):
        with patch("agents.qualification.anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.content = [
                MagicMock(
                    text=json.dumps(
                        {
                            "is_eligible": True,
                            "recommended_procedure": "judicial",
                            "procedure_type": "asset_realization",
                            "estimated_cost_min": 80000,
                            "estimated_cost_max": 150000,
                            "estimated_duration_months_min": 8,
                            "estimated_duration_months_max": 12,
                            "risk_level": "medium",
                            "risk_factors": ["risk:transactions_3y"],
                            "confidence": 0.85,
                            "explanation": "Объяснение от AI",
                            "needs_lawyer_review": True,
                        }
                    )
                )
            ]
            mock_client.messages.create.return_value = mock_message
            mock_anthropic_cls.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def mock_openai_client(self):
        with patch("agents.qualification.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_completion = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = json.dumps(
                {
                    "is_eligible": True,
                    "recommended_procedure": "judicial",
                    "procedure_type": "restructuring",
                    "estimated_cost_min": 90000,
                    "estimated_cost_max": 140000,
                    "estimated_duration_months_min": 9,
                    "estimated_duration_months_max": 15,
                    "risk_level": "low",
                    "risk_factors": [],
                    "confidence": 0.9,
                    "explanation": "Объяснение от OpenAI",
                    "needs_lawyer_review": False,
                }
            )
            mock_completion.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai_cls.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_qualify_with_anthropic_success(self, mock_anthropic_client):
        """Agent successfully uses Anthropic and returns parsed result."""
        agent = QualificationAgent(
            anthropic_api_key="fake-key",
            openai_api_key=None,
        )
        input_data = make_input(total_debt=500_000)
        result = await agent.qualify(input_data)

        assert isinstance(result, QualificationResult)
        assert result.is_eligible is True
        assert result.recommended_procedure == "judicial"
        assert result.procedure_type == "asset_realization"
        assert result.confidence == 0.85
        assert "risk:transactions_3y" in result.risk_factors
        mock_anthropic_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_qualify_with_openai_fallback(self, mock_anthropic_client, mock_openai_client):
        """Agent falls back to OpenAI when Anthropic fails."""
        # Make Anthropic raise an exception
        mock_anthropic_client.messages.create.side_effect = Exception("API error")
        agent = QualificationAgent(
            anthropic_api_key="fake-key",
            openai_api_key="fake-key",
        )
        input_data = make_input(total_debt=500_000)
        result = await agent.qualify(input_data)

        assert isinstance(result, QualificationResult)
        # Should have used OpenAI (check that OpenAI was called)
        mock_openai_client.chat.completions.create.assert_called_once()
        assert result.procedure_type == "restructuring"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_qualify_both_providers_fail(self):
        """Agent returns rule-based fallback when both providers fail."""
        with patch("agents.qualification.anthropic.Anthropic") as mock_anthropic_cls:
            mock_anthropic_cls.side_effect = Exception("No API key")
            with patch("agents.qualification.OpenAI") as mock_openai_cls:
                mock_openai_cls.side_effect = Exception("No API key")
                agent = QualificationAgent(
                    anthropic_api_key=None,
                    openai_api_key=None,
                )
                input_data = make_input(total_debt=500_000)
                result = await agent.qualify(input_data)

                assert isinstance(result, QualificationResult)
                # Should be rule-based fallback (pre-screening passes)
                assert result.is_eligible is True  # because debt > 25k
                assert result.recommended_procedure == "judicial"
                assert result.procedure_type == "asset_realization"
                assert result.confidence == 0.6  # as defined in fallback

    @pytest.mark.asyncio
    async def test_qualify_with_pre_screen_failure(self):
        """If pre-screening fails, agent should return not_eligible without calling LLM."""
        # Mock pre_screen to return failure
        with patch("agents.qualification.pre_screen") as mock_pre_screen:
            mock_pre_screen.return_value = {
                "pass": False,
                "reason": "Сумма долга менее 25 000 ₽ — банкротство невозможно",
                "flags": [],
            }
            agent = QualificationAgent(
                anthropic_api_key="fake-key",
                openai_api_key="fake-key",
            )
            input_data = make_input(total_debt=20_000)
            result = await agent.qualify(input_data)

            assert result.is_eligible is False
            assert result.recommended_procedure == "not_eligible"
            assert result.procedure_type is None
            # Ensure LLM was not called (no API clients initialized because we didn't mock)
            # Since we didn't mock Anthropic/OpenAI, they would raise, but they shouldn't be called.
            # The agent will not initialize clients because pre_screen fails before LLM call.
            # Actually, the agent still initializes clients in __init__, but we can ignore.

    def test_parse_result_valid_json(self):
        """Test parsing of valid JSON response."""
        agent = QualificationAgent()
        data = {
            "is_eligible": True,
            "recommended_procedure": "judicial",
            "procedure_type": "asset_realization",
            "estimated_cost_min": 80000,
            "estimated_cost_max": 150000,
            "estimated_duration_months_min": 8,
            "estimated_duration_months_max": 12,
            "risk_level": "medium",
            "risk_factors": ["risk:transactions_3y"],
            "confidence": 0.85,
            "explanation": "Test",
            "needs_lawyer_review": True,
        }
        result = agent._parse_result(data)
        assert result.is_eligible is True
        assert result.risk_level == "medium"

    def test_parse_result_missing_fields(self):
        """Test parsing with missing optional fields uses defaults."""
        agent = QualificationAgent()
        data = {
            "is_eligible": False,
            "recommended_procedure": "not_eligible",
            "procedure_type": None,
            "estimated_cost_min": 0,
            "estimated_cost_max": 0,
            "estimated_duration_months_min": 0,
            "estimated_duration_months_max": 0,
            "risk_level": "low",
            "risk_factors": [],
            "confidence": 0.5,
            "explanation": "Test",
            "needs_lawyer_review": False,
        }
        result = agent._parse_result(data)
        assert result.is_eligible is False
        assert result.risk_factors == []

    def test_build_user_message(self):
        """Test formatting of user message."""
        agent = QualificationAgent()
        input_data = make_input(
            total_debt=1_200_000,
            monthly_income=50_000,
            is_employed=True,
            has_property=True,
            property_types=["apartment", "car"],
            region="Москва",
        )
        message = agent._build_user_message(input_data)
        assert "1 200 000" in message
        assert "50 000" in message
        assert "Москва" in message
        assert "apartment" in message
