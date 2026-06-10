"""Tests for ArgumentEvidenceAgent — evidence & fallacy detection."""

import pytest
from app.agents.argument_evidence import ArgumentEvidenceAgent


@pytest.fixture
def agent(mock_llm):
    return ArgumentEvidenceAgent(mock_llm)


class TestBuildUserMessage:
    def test_includes_document_text(self, agent):
        msg = agent._build_user_message(
            document_text="Paper content here.",
            evidence_patterns='{"min_evidence": 3}',
            competition_type="research",
        )
        assert "Paper content here." in msg
        assert "research" in msg
        assert "证据标准配置" in msg

    def test_includes_type_hint_for_research(self, agent):
        msg = agent._build_user_message(
            document_text="text",
            evidence_patterns="{}",
            competition_type="research",
        )
        assert "科研型论文" in msg
        assert "hypothesis" in msg

    def test_includes_type_hint_for_discursive(self, agent):
        msg = agent._build_user_message(
            document_text="text",
            evidence_patterns="{}",
            competition_type="discursive",
        )
        assert "思辨型议论文" in msg
        assert "counterargument" in msg

    def test_includes_type_hint_for_math_modeling(self, agent):
        msg = agent._build_user_message(
            document_text="text",
            evidence_patterns="{}",
            competition_type="math_modeling",
        )
        assert "数学建模论文" in msg
        assert "灵敏度分析" in msg

    def test_includes_type_hint_for_business_case(self, agent):
        msg = agent._build_user_message(
            document_text="text",
            evidence_patterns="{}",
            competition_type="business_case",
        )
        assert "商科案例报告" in msg
        assert "SWOT" in msg

    def test_unknown_type_no_hint(self, agent):
        msg = agent._build_user_message(
            document_text="text",
            evidence_patterns="{}",
            competition_type="unknown_type",
        )
        # Should not crash, just no hint
        assert "竞赛专项提示" not in msg or "unknown_type" in msg


class TestRun:
    @pytest.mark.asyncio
    async def test_run_with_mock(self, agent, mock_llm):
        mock_llm.set_response({
            "argument_score": 7.5,
            "evidence_score": 7.0,
            "overall_score": 7.2,
            "claims": [],
            "logical_fallacies": [],
            "validation_point": {"type": "null"},
            "quantitative_check": {"applicable": False},
            "source_quality": {"total_citations": 0},
            "overall_assessment": "Good",
            "positive_points": ["Clear argument"],
            "key_issues": ["Needs more evidence"],
        })
        result = await agent.run(
            document_text="Sample paper.",
            competition_type="research",
        )
        assert result["agent"] == "ArgumentEvidence"
        assert result["overall_score"] == 7.2
