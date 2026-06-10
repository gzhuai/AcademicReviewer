"""
Shared test fixtures for AcademicReviewer.

Provides:
- sample_isef_text / sample_jl_text: real paper texts from fixtures/
- sample_refs_section: extracted references section for citation tests
- MockLLMAdapter: controllable mock for Agent tests
- sample_features: synthetic feature dicts for calibration tests
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.llm.base import LLMAdapter

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ── Text fixtures ────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_isef_text() -> str:
    """Load the sample ISEF research paper."""
    return (FIXTURES_DIR / "sample_isef_paper.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def sample_jl_text() -> str:
    """Load a sample John Locke discursive essay."""
    path = FIXTURES_DIR / "john_locke_sample.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    # Fallback: use the second sample
    return (FIXTURES_DIR / "john_locke_sample_2.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def sample_refs_section() -> str:
    """A minimal APA-style references section for citation tests."""
    return """Barnes, D. K., Galgani, F., Thompson, R. C., & Barlaz, M. (2009). Accumulation and fragmentation of plastic debris in global environments. Philosophical Transactions of the Royal Society B, 364(1526), 1985-1998.

Cole, M., Lindeque, P., Halsband, C., & Galloway, T. S. (2011). Microplastics as contaminants in the marine environment: A review. Marine Pollution Bulletin, 62(12), 2588-2597.

Smith, J. A., & Jones, K. L. (2020). Effects of environmental stressors on Daphnia populations. Journal of Freshwater Ecology, 35(1), 45-62."""


# ── Mock LLM Adapter ─────────────────────────────────────────

class MockLLMAdapter(LLMAdapter):
    """Configurable mock LLM adapter for testing agents without network calls.

    Usage in tests::

        mock_llm = MockLLMAdapter()
        mock_llm.set_response({"structure_score": 8.5})
        agent = StructureLogicAgent(mock_llm)
        result = await agent.run(document_text="...", competition_type="research")
        assert mock_llm.chat_calls[0]["system"] is not None
    """

    def __init__(self, default_response: dict | None = None):
        self._responses: dict[str, str] = {}
        self._default = json.dumps(default_response or {"score": 7.0, "agent": "mock"})
        self.chat_calls: list[dict] = []

    def set_response(self, data: dict) -> None:
        """Set the next JSON response returned by chat()."""
        self._default = json.dumps(data)

    def set_response_for_keyword(self, keyword: str, data: dict) -> None:
        """Return `data` when `user_message` contains `keyword`."""
        self._responses[keyword] = json.dumps(data)

    async def chat(
        self,
        system_prompt: str = "",
        user_message: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        self.chat_calls.append({
            "system": system_prompt,
            "user": user_message,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        for keyword, response in self._responses.items():
            if keyword in user_message:
                return response
        return self._default

    def model_name(self) -> str:
        return "mock-model"

    def provider_name(self) -> str:
        return "mock"


@pytest.fixture
def mock_llm() -> MockLLMAdapter:
    """Return a fresh MockLLMAdapter for a single test."""
    return MockLLMAdapter()


# ── Calibration test data ────────────────────────────────────

@pytest.fixture
def sample_winners_features() -> list[dict]:
    """Simulated feature dicts for 3 winning papers."""
    return [
        {
            "filename": "winner_1.txt", "word_count": 3500,
            "avg_sentence_length": 22.5, "sentence_length_std": 8.2,
            "citation_density": 4.2, "passive_voice_ratio": 0.15,
            "vocabulary_diversity": 0.72, "logical_marker_density": 3.5,
            "transition_frequency": 4.1, "avg_paragraph_length": 120.0,
            "section_coverage": 0.875, "has_p_value": 1.0,
            "has_effect_size": 1.0, "has_control_group": 1.0,
            "has_sample_size": 1.0, "evidence_diversity_score": 0.8,
            "evidence_source_count": 4, "claim_count_estimate": 12,
            "hook_sentence_present": 1.0, "gap_statement_present": 1.0,
            "limitations_section_present": 1.0, "future_work_mentioned": 1.0,
        },
        {
            "filename": "winner_2.txt", "word_count": 4200,
            "avg_sentence_length": 20.1, "sentence_length_std": 7.5,
            "citation_density": 5.1, "passive_voice_ratio": 0.12,
            "vocabulary_diversity": 0.75, "logical_marker_density": 4.0,
            "transition_frequency": 4.5, "avg_paragraph_length": 135.0,
            "section_coverage": 1.0, "has_p_value": 1.0,
            "has_effect_size": 1.0, "has_control_group": 1.0,
            "has_sample_size": 1.0, "evidence_diversity_score": 1.0,
            "evidence_source_count": 5, "claim_count_estimate": 15,
            "hook_sentence_present": 1.0, "gap_statement_present": 1.0,
            "limitations_section_present": 1.0, "future_work_mentioned": 1.0,
        },
        {
            "filename": "winner_3.txt", "word_count": 3800,
            "avg_sentence_length": 21.3, "sentence_length_std": 8.8,
            "citation_density": 4.8, "passive_voice_ratio": 0.14,
            "vocabulary_diversity": 0.70, "logical_marker_density": 3.8,
            "transition_frequency": 3.9, "avg_paragraph_length": 110.0,
            "section_coverage": 0.875, "has_p_value": 1.0,
            "has_effect_size": 0.0, "has_control_group": 1.0,
            "has_sample_size": 1.0, "evidence_diversity_score": 0.8,
            "evidence_source_count": 4, "claim_count_estimate": 14,
            "hook_sentence_present": 1.0, "gap_statement_present": 1.0,
            "limitations_section_present": 1.0, "future_work_mentioned": 1.0,
        },
    ]


@pytest.fixture
def sample_losers_features() -> list[dict]:
    """Simulated feature dicts for 3 losing papers."""
    return [
        {
            "filename": "loser_1.txt", "word_count": 2800,
            "avg_sentence_length": 18.2, "sentence_length_std": 12.5,
            "citation_density": 1.5, "passive_voice_ratio": 0.35,
            "vocabulary_diversity": 0.55, "logical_marker_density": 1.2,
            "transition_frequency": 1.5, "avg_paragraph_length": 200.0,
            "section_coverage": 0.5, "has_p_value": 0.0,
            "has_effect_size": 0.0, "has_control_group": 0.0,
            "has_sample_size": 0.0, "evidence_diversity_score": 0.2,
            "evidence_source_count": 1, "claim_count_estimate": 5,
            "hook_sentence_present": 0.0, "gap_statement_present": 0.0,
            "limitations_section_present": 0.0, "future_work_mentioned": 0.0,
        },
        {
            "filename": "loser_2.txt", "word_count": 3100,
            "avg_sentence_length": 17.0, "sentence_length_std": 14.2,
            "citation_density": 1.2, "passive_voice_ratio": 0.40,
            "vocabulary_diversity": 0.50, "logical_marker_density": 0.9,
            "transition_frequency": 1.3, "avg_paragraph_length": 250.0,
            "section_coverage": 0.375, "has_p_value": 0.0,
            "has_effect_size": 0.0, "has_control_group": 0.0,
            "has_sample_size": 0.0, "evidence_diversity_score": 0.0,
            "evidence_source_count": 0, "claim_count_estimate": 3,
            "hook_sentence_present": 0.0, "gap_statement_present": 0.0,
            "limitations_section_present": 0.0, "future_work_mentioned": 0.0,
        },
        {
            "filename": "loser_3.txt", "word_count": 2500,
            "avg_sentence_length": 16.5, "sentence_length_std": 16.0,
            "citation_density": 0.8, "passive_voice_ratio": 0.45,
            "vocabulary_diversity": 0.48, "logical_marker_density": 0.7,
            "transition_frequency": 1.1, "avg_paragraph_length": 300.0,
            "section_coverage": 0.5, "has_p_value": 0.0,
            "has_effect_size": 0.0, "has_control_group": 0.0,
            "has_sample_size": 1.0, "evidence_diversity_score": 0.2,
            "evidence_source_count": 1, "claim_count_estimate": 4,
            "hook_sentence_present": 0.0, "gap_statement_present": 1.0,
            "limitations_section_present": 0.0, "future_work_mentioned": 0.0,
        },
    ]


@pytest.fixture
def feature_name_list() -> list[str]:
    """The authoritative list of feature names from feature_extractor."""
    from app.calibration.feature_extractor import feature_names
    return feature_names()
