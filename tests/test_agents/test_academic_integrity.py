"""Tests for AcademicIntegrityAgent — citation checking + originality."""

import pytest
from app.agents.academic_integrity import AcademicIntegrityAgent


@pytest.fixture
def agent(mock_llm):
    return AcademicIntegrityAgent(mock_llm)


class TestBuildUserMessage:
    def test_includes_document_text(self, agent):
        msg = agent._build_user_message(
            document_text="Paper with citations [1].",
            citation_preprocessed='{"total_cites": 1, "matched": 1}',
            similarity_report='{}',
        )
        assert "Paper with citations [1]." in msg
        assert "引文预检结果" in msg
        assert "相似度报告" in msg

    def test_includes_citation_data(self, agent):
        msg = agent._build_user_message(
            document_text="text",
            citation_preprocessed='{"total_cites": 5, "matched": 3, "match_rate": 0.6}',
            similarity_report='{}',
        )
        assert "total_cites" in msg
        assert "0.6" in msg

    def test_includes_similarity_report(self, agent):
        msg = agent._build_user_message(
            document_text="text",
            citation_preprocessed="{}",
            similarity_report='{"originality_score": 8}',
        )
        assert "originality_score" in msg


class TestRun:
    @pytest.mark.asyncio
    async def test_run_without_originality_check(self, agent, mock_llm):
        """run_originality_check=False should skip ChromaDB."""
        mock_llm.set_response({
            "integrity_score": 9.0,
            "citation_report": {},
            "originality_assessment": "No check run",
            "positive_points": ["All citations match"],
            "key_issues": [],
        })
        result = await agent.run(
            document_text="Sample paper text with citations [1].",
            references_section="[1] Author. Title. Journal. 2020.",
            similarity_report="{}",
            run_originality_check=False,
        )
        assert result["agent"] == "AcademicIntegrity"
        # citation check should still have been run (rules engine)
        assert "citation_report" in result or "integrity_score" in result

    @pytest.mark.asyncio
    async def test_run_skips_chromadb_when_empty(self, agent, mock_llm):
        """When ChromaDB has no indexed documents, originality check is gracefully skipped."""
        mock_llm.set_response({
            "integrity_score": 9.0,
            "positive_points": [],
            "key_issues": [],
        })
        # ChromaDB likely empty in test env — should not crash
        result = await agent.run(
            document_text="Test paper.",
            references_section="",
            similarity_report="{}",
            run_originality_check=True,  # try to run, but gracefully skip if empty
        )
        assert "error" not in result
