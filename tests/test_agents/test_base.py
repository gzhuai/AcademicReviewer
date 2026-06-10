"""Unit tests for app/agents/base.py — BaseAgent with mock LLM."""

import pytest
from pathlib import Path

from app.agents.base import BaseAgent


class _SimpleAgent(BaseAgent):
    """Concrete agent for testing BaseAgent functionality."""
    agent_name = "SimpleAgent"
    prompt_template_path = "a1_rubric_parser.txt"  # use an existing prompt


class _NoPromptAgent(BaseAgent):
    """Agent with a non-existent prompt template path."""
    agent_name = "NoPromptAgent"
    prompt_template_path = "nonexistent_prompt.txt"


@pytest.fixture
def simple_agent(mock_llm):
    return _SimpleAgent(mock_llm)


@pytest.fixture
def no_prompt_agent(mock_llm):
    return _NoPromptAgent(mock_llm)


class TestLoadPrompt:
    def test_load_existing_prompt(self, simple_agent):
        """Should load a1_rubric_parser.txt from prompts/ directory."""
        assert simple_agent.template != ""
        assert "评分标准" in simple_agent.template or "rubric" in simple_agent.template.lower()

    def test_load_missing_prompt(self, no_prompt_agent):
        """Missing prompt should result in empty template, not crash."""
        assert no_prompt_agent.template == ""


class TestBuildSystemPrompt:
    def test_returns_template(self, simple_agent):
        prompt = simple_agent._build_system_prompt()
        assert prompt == simple_agent.template

    def test_ignores_extra_kwargs(self, simple_agent):
        """Extra kwargs should not affect the system prompt (default impl)."""
        prompt = simple_agent._build_system_prompt(extra="value", foo="bar")
        assert prompt == simple_agent.template


class TestBuildUserMessage:
    def test_default_returns_json(self, simple_agent):
        msg = simple_agent._build_user_message(key1="value1", key2=42)
        assert "key1" in msg
        assert "value1" in msg
        assert "key2" in msg
        assert "42" in msg

    def test_empty_kwargs(self, simple_agent):
        msg = simple_agent._build_user_message()
        assert msg == "{}"


class TestRun:
    @pytest.mark.asyncio
    async def test_successful_run(self, simple_agent, mock_llm):
        mock_llm.set_response({"score": 8.5, "summary": "Good work"})
        result = await simple_agent.run(document_text="Test document")

        assert result["agent"] == "SimpleAgent"
        assert result["score"] == 8.5
        assert result["summary"] == "Good work"
        assert result["model"] == "mock-model"
        assert result["provider"] == "mock"
        assert isinstance(result["duration_seconds"], float)
        assert result["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_includes_metadata(self, simple_agent, mock_llm):
        mock_llm.set_response({"result": "ok"})
        result = await simple_agent.run(input="test")

        assert "agent" in result
        assert "model" in result
        assert "provider" in result
        assert "duration_seconds" in result

    @pytest.mark.asyncio
    async def test_calls_mock_llm(self, simple_agent, mock_llm):
        mock_llm.set_response({"data": "response"})
        await simple_agent.run(text="hello")

        assert len(mock_llm.chat_calls) == 1
        call = mock_llm.chat_calls[0]
        assert "system" in call
        assert "user" in call
        assert call["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_llm_error_returns_error_dict(self, simple_agent, mock_llm):
        """When the mock LLM raises, the agent should catch it and return an error dict."""

        class _FailingMock(mock_llm.__class__):
            async def chat(self, system_prompt="", user_message="", temperature=0.3, max_tokens=4096):
                raise RuntimeError("Simulated LLM failure")

        failing_llm = _FailingMock()
        agent = _SimpleAgent(failing_llm)

        result = await agent.run(text="test")
        assert "error" in result
        assert "Simulated LLM failure" in result["error"]
        assert result["agent"] == "SimpleAgent"


class TestLoadJson:
    def test_load_valid_json_file(self):
        """_load_json should load a real JSON file from configs/."""
        # Use the competition registry which always exists
        path = Path(__file__).resolve().parent.parent.parent / "configs" / "competition_registry.json"
        data = BaseAgent._load_json(str(path))
        assert isinstance(data, dict)
        assert "competitions" in data

    def test_load_relative_path(self):
        """Relative paths should be resolved relative to project root."""
        data = BaseAgent._load_json("configs/competition_registry.json")
        assert isinstance(data, dict)
        assert "competitions" in data

    def test_load_nonexistent_file(self):
        data = BaseAgent._load_json("configs/nonexistent_file_xyz.json")
        assert data == {}
