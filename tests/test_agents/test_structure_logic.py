"""Tests for StructureLogicAgent — structure & logic review."""

import pytest
from app.agents.structure_logic import StructureLogicAgent


@pytest.fixture
def agent(mock_llm):
    return StructureLogicAgent(mock_llm)


class TestBuildUserMessage:
    def test_includes_document_text(self, agent):
        msg = agent._build_user_message(
            document_text="This is a test paper.",
            structure_schema='{"required_sections": []}',
            competition_type="research",
        )
        assert "This is a test paper." in msg
        assert "research" in msg
        assert "结构 Schema" in msg

    def test_includes_competition_type(self, agent):
        msg = agent._build_user_message(
            document_text="text",
            structure_schema="{}",
            competition_type="discursive",
        )
        assert "discursive" in msg


class TestRun:
    @pytest.mark.asyncio
    async def test_run_with_mock(self, agent, mock_llm):
        mock_llm.set_response({
            "structure_score": 8.0,
            "sections_found": ["Introduction", "Body", "Conclusion"],
            "missing_sections": [],
            "section_issues": [],
            "logic_issues": [],
            "main_argument_coaching": {"current_statement": "test"},
            "duplication_report": [],
            "positive_points": ["Good structure"],
            "key_issues": [],
        })
        result = await agent.run(
            document_text="Sample paper text.",
            competition_type="research",
        )
        assert result["agent"] == "StructureLogic"
        assert result["structure_score"] == 8.0
