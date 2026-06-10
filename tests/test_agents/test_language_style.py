"""Tests for LanguageStyleAgent — grammar, style, spelling."""

import pytest
from app.agents.language_style import LanguageStyleAgent


@pytest.fixture
def agent(mock_llm):
    return LanguageStyleAgent(mock_llm)


class TestBuildUserMessage:
    def test_includes_document_text(self, agent):
        msg = agent._build_user_message(document_text="The quick brown fox.")
        assert "The quick brown fox." in msg

    def test_with_style_guide(self, agent):
        msg = agent._build_user_message(
            document_text="Paper text.",
            style_guide_context='{"formality": "academic", "voice": "active"}',
        )
        assert "风格指南" in msg
        assert "academic" in msg

    def test_without_style_guide(self, agent):
        msg = agent._build_user_message(document_text="Paper text.")
        # Should not include style guide section
        assert "风格指南" not in msg


class TestRun:
    @pytest.mark.asyncio
    async def test_run_with_mock(self, agent, mock_llm):
        mock_llm.set_response({
            "language_score": 8.5,
            "rewrites": [
                {"location": "第1段", "original": "recieved", "corrected": "received", "issue_type": "spelling"}
            ],
            "suggestions": [
                {"location": "第2段", "description": "Consider passive → active voice", "type": "style"}
            ],
            "positive_points": ["Good academic tone"],
            "key_issues": ["Occasional spelling errors"],
        })
        result = await agent.run(document_text="Sample text.")
        assert result["agent"] == "LanguageStyle"
        assert result["language_score"] == 8.5
