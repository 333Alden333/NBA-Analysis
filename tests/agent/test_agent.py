"""Tests for agent factory and system prompt."""

from unittest.mock import patch, MagicMock

import pytest


class TestAgentFactory:
    def test_create_agent_returns_agent_with_tools(self, session):
        from hermes.agent.agent import create_agent

        with patch("hermes.agent.agent.LiteLLMModel") as MockModel:
            mock_model = MagicMock()
            MockModel.return_value = mock_model

            agent = create_agent(session)

            # Should have all 8 custom tools (plus built-in like final_answer)
            assert len(agent.tools) >= 8

    def test_create_agent_tool_names(self, session):
        from hermes.agent.agent import create_agent

        with patch("hermes.agent.agent.LiteLLMModel") as MockModel:
            MockModel.return_value = MagicMock()

            agent = create_agent(session)

            # agent.tools is a dict keyed by tool name
            tool_names = list(agent.tools.keys())
            expected = [
                "search_player", "get_player_stats", "get_player_predictions",
                "get_team_info", "get_today_games", "get_prediction_accuracy",
                "get_prediction_history", "get_matchup_analysis",
            ]
            for name in expected:
                assert name in tool_names, f"Tool '{name}' not found in {tool_names}"


class TestSystemPrompt:
    def test_prompt_contains_key_phrases(self):
        from hermes.agent.agent import HERMES_SYSTEM_PROMPT

        prompt = HERMES_SYSTEM_PROMPT
        assert "NBA" in prompt
        assert "tool" in prompt.lower()
        assert "prediction" in prompt.lower()

    def test_prompt_has_format_placeholders(self):
        from hermes.agent.agent import HERMES_SYSTEM_PROMPT

        # Should have {today} and {model_version} placeholders
        assert "{today}" in HERMES_SYSTEM_PROMPT
        assert "{model_version}" in HERMES_SYSTEM_PROMPT


class TestCheckOllama:
    def test_check_returns_bool(self):
        from hermes.agent.agent import check_ollama_connection

        with patch("hermes.agent.agent.requests") as mock_req:
            mock_req.get.return_value = MagicMock(status_code=200)
            assert check_ollama_connection() is True

    def test_check_handles_connection_error(self):
        from hermes.agent.agent import check_ollama_connection

        with patch("hermes.agent.agent.requests") as mock_req:
            mock_req.get.side_effect = Exception("Connection refused")
            assert check_ollama_connection() is False
