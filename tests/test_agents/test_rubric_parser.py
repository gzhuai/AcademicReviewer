"""Tests for RubricParserAgent — competition rubric parsing."""

import pytest
from app.agents.rubric_parser import RubricParserAgent


@pytest.fixture
def agent(mock_llm):
    return RubricParserAgent(mock_llm)


class TestBuildUserMessage:
    def test_includes_rubric_text(self, agent):
        msg = agent._build_user_message(rubric_text='{"criteria": ["clarity", "depth"]}')
        assert "clarity" in msg
        assert "depth" in msg

    def test_prompt_structure(self, agent):
        msg = agent._build_user_message(rubric_text="Test rubric content")
        assert "Test rubric content" in msg
        assert "评分标准" in msg.lower() or "解析" in msg


class TestRun:
    @pytest.mark.asyncio
    async def test_run_with_mock(self, agent, mock_llm):
        mock_llm.set_response({
            "rubric_score": 7.0,
            "dimensions": [
                {"name": "Research Quality", "weight": 0.4, "max_score": 10}
            ],
            "scoring_notes": "Standard ISEF rubric applied.",
        })
        result = await agent.run(
            rubric_text='{"dimensions": [{"name": "Research Quality", "weight": 0.4}]}'
        )
        assert result["agent"] == "RubricParser"
        assert result["rubric_score"] == 7.0
