"""Tests for confidence_engine.py — rule-based confidence label assignment."""

import pytest
from app.utils.confidence_engine import (
    apply_confidence_labels,
    get_substitutability_emoji,
    get_substitutability_label,
    get_substitutability_description,
)


class TestApplyConfidenceLabels:
    """Test that the rule engine correctly assigns substitutability labels."""

    def test_language_rewrites_get_full(self):
        result = {
            "agent": "LanguageStyle",
            "rewrites": [
                {"original": "recieve", "corrected": "receive", "issue": "spelling", "location": "第1段 第2句"},
                {"original": "they is", "corrected": "they are", "issue": "grammar", "location": "第2段 第1句"},
                {"original": "hello.", "corrected": "hello。", "issue": "punctuation", "location": "第3段 第3句"},
            ],
            "suggestions": [],
        }
        out = apply_confidence_labels("LanguageStyle", result)
        for rw in out["rewrites"]:
            assert rw["substitutability"] == "FULL"

    def test_language_suggestions_get_review(self):
        result = {
            "agent": "LanguageStyle",
            "rewrites": [],
            "suggestions": [
                {"type": "passive_voice", "substitutability": "FULL"},
                {"type": "sentence_length", "substitutability": "FULL"},
                {"type": "word_choice"},
            ],
        }
        out = apply_confidence_labels("LanguageStyle", result)
        assert out["suggestions"][0]["substitutability"] == "REVIEW"  # overridden from FULL
        assert out["suggestions"][1]["substitutability"] == "REVIEW"  # overridden from FULL
        assert out["suggestions"][2]["substitutability"] == "REVIEW"  # default

    def test_language_redundancy_gets_full(self):
        result = {
            "agent": "LanguageStyle",
            "rewrites": [],
            "suggestions": [{"type": "redundancy"}],
        }
        out = apply_confidence_labels("LanguageStyle", result)
        assert out["suggestions"][0]["substitutability"] == "FULL"

    def test_structure_logic_applies_severity_rules(self):
        result = {
            "agent": "StructureLogic",
            "section_issues": [
                {"severity": "high"},
                {"severity": "medium"},
                {"severity": "low"},
                {},  # no severity
            ],
            "logic_issues": [],
        }
        out = apply_confidence_labels("StructureLogic", result)
        assert out["section_issues"][0]["substitutability"] == "FULL"
        assert out["section_issues"][1]["substitutability"] == "REVIEW"
        assert out["section_issues"][2]["substitutability"] == "REVIEW"
        assert out["section_issues"][3]["substitutability"] == "REVIEW"  # default

    def test_structure_logic_issues_default_review(self):
        result = {
            "agent": "StructureLogic",
            "section_issues": [],
            "logic_issues": [
                {"type": "gap"},
                {"type": "jump"},
            ],
        }
        out = apply_confidence_labels("StructureLogic", result)
        for li in out["logic_issues"]:
            assert li["substitutability"] == "REVIEW"

    def test_argument_fallacies_type_rules(self):
        result = {
            "agent": "ArgumentEvidence",
            "claims": [],
            "logical_fallacies": [
                {"fallacy_type": "begging_question"},
                {"fallacy_type": "false_dichotomy"},
                {"fallacy_type": "straw_man"},
                {"fallacy_type": "weak_analogy"},
                {"fallacy_type": "unknown_type"},  # default
            ],
        }
        out = apply_confidence_labels("ArgumentEvidence", result)
        assert out["logical_fallacies"][0]["substitutability"] == "FULL"
        assert out["logical_fallacies"][1]["substitutability"] == "FULL"
        assert out["logical_fallacies"][2]["substitutability"] == "REVIEW"
        assert out["logical_fallacies"][3]["substitutability"] == "REVIEW"
        assert out["logical_fallacies"][4]["substitutability"] == "REVIEW"

    def test_argument_claims_default_review(self):
        result = {
            "agent": "ArgumentEvidence",
            "claims": [
                {"claim": "test"},
                {"claim": "test2", "substitutability": "FULL"},  # LLM tried to claim FULL
            ],
            "logical_fallacies": [],
        }
        out = apply_confidence_labels("ArgumentEvidence", result)
        # Rules override: claims are always REVIEW per rule engine
        assert out["claims"][0]["substitutability"] == "REVIEW"
        assert out["claims"][1]["substitutability"] == "REVIEW"

    def test_academic_integrity_labels(self):
        result = {
            "agent": "AcademicIntegrity",
            "citation_report": {"match_rate": 1.0},
            "originality_report": {"originality_score": 9.0},
        }
        out = apply_confidence_labels("AcademicIntegrity", result)
        assert out["citation_report"]["substitutability"] == "FULL"
        assert out["originality_report"]["substitutability"] == "ESCALATE"

    def test_none_input_returns_none(self):
        assert apply_confidence_labels("LanguageStyle", None) is None

    def test_non_dict_input_returns_unchanged(self):
        assert apply_confidence_labels("LanguageStyle", "not a dict") == "not a dict"

    def test_empty_result(self):
        result = {}
        out = apply_confidence_labels("LanguageStyle", result)
        assert out == {}

    def test_unknown_agent_no_crash(self):
        result = {"some": "data"}
        out = apply_confidence_labels("UnknownAgent", result)
        assert out == {"some": "data"}


class TestSubstitutabilityHelpers:
    def test_emoji_mapping(self):
        assert get_substitutability_emoji("FULL") == ""
        assert get_substitutability_emoji("REVIEW") == "⚡"
        assert get_substitutability_emoji("ESCALATE") == "🔴"
        assert get_substitutability_emoji("UNKNOWN") == ""

    def test_label_mapping(self):
        assert get_substitutability_label("FULL") == "FULL"
        assert get_substitutability_label("REVIEW") == "REVIEW"
        assert get_substitutability_label("ESCALATE") == "ESCALATE"
        assert get_substitutability_label("UNKNOWN") == "REVIEW"

    def test_description_mapping(self):
        assert "无需审核" in get_substitutability_description("FULL")
        assert "需老师确认" in get_substitutability_description("REVIEW")
        assert "必须老师审核" in get_substitutability_description("ESCALATE")
        assert get_substitutability_description("UNKNOWN") == ""
