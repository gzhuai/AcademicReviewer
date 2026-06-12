"""Tests for student_level.py — heuristic student level estimation."""

import pytest
from app.utils.student_level import (
    estimate_student_level,
    StudentLevel,
    LevelEstimation,
)


class TestEstimateStudentLevel:
    def test_empty_text_returns_beginner(self):
        result = estimate_student_level("")
        assert result.level == StudentLevel.BEGINNER
        assert result.word_count == 0

    def test_short_simple_text_beginner(self):
        # Very short text with truly simple structure
        text = "Hi. Ok. Yes. No. Go."
        result = estimate_student_level(text)
        assert result.level == StudentLevel.BEGINNER

    def test_medium_text_intermediate(self):
        # ~200 words with moderate complexity
        text = (
            "The impact of social media on adolescent mental health has been "
            "a topic of increasing scholarly attention in recent years. "
            "Researchers have conducted numerous studies examining these effects. "
            "The results suggest that prolonged exposure may contribute to "
            "anxiety and depression among young people. However some scholars "
            "disagree about the causal mechanisms involved. They argue that "
            "other factors such as pre-existing conditions play a larger role. "
            "Furthermore the relationship between screen time and wellbeing "
            "appears to be more complex than initially assumed. Additional "
            "research is needed to understand these dynamics more fully. "
            "The implications for public health policy are significant and "
            "warrant careful consideration from multiple perspectives including "
            "psychological sociological and educational viewpoints. "
        ) * 4  # roughly 200 words
        result = estimate_student_level(text)
        # Should be at least intermediate
        assert result.level in (StudentLevel.INTERMEDIATE, StudentLevel.ADVANCED)

    def test_long_complex_text_advanced(self):
        # ~3000 words with very diverse vocabulary (>0.06 TTR requires ~180+ unique types)
        words_pool = [
            "epistemological", "methodological", "paradigmatic", "diachronic",
            "hermeneutic", "phenomenological", "ontological", "teleological",
            "heuristic", "dialectical", "synthesis", "pragmatic", "normative",
            "empirical", "theoretical", "conceptual", "analytical", "systemic",
            "structural", "functional", "cognitive", "behavioral", "neural",
            "genetic", "evolutionary", "ecological", "socioeconomic", "political",
            "institutional", "organizational", "technological", "informational",
            "quantum", "relativistic", "thermodynamic", "electromagnetic",
            "biochemical", "pharmacological", "epidemiological", "immunological",
            "anthropological", "archaeological", "linguistic", "semiotic",
            "pedagogical", "andragogical", "cybernetic", "algorithmic",
            "stochastic", "deterministic", "probabilistic", "categorical",
            "metaphysical", "transcendental", "existential", "phenomenal",
            "discursive", "recursive", "iterative", "convergent", "divergent",
            "asymptotic", "polynomial", "exponential", "logarithmic", "fractal",
            "topological", "differential", "integral", "multivariate", "nonlinear",
            "isomorphic", "homomorphic", "symplectic", "riemannian", "euclidean",
            "cartesian", "newtonian", "darwinian", "freudian", "jungian",
            "marxist", "hegelian", "kantian", "nietzschean", "socratic",
            "aristotelian", "platonic", "homeric", "shakespearean", "miltonic",
            "revolutionary", "counterrevolutionary", "postmodern", "neoclassical",
            "deconstructionist", "structuralist", "poststructuralist", "modernist",
            "impressionist", "expressionist", "surrealist", "minimalist",
            "maximalist", "constructivist", "reductionist", "holistic",
            "emergent", "complex", "adaptive", "resilient", "sustainable",
            "regenerative", "transformative", "disruptive", "innovative",
            "cumulative", "additive", "multiplicative", "distributive",
            "commutative", "associative", "transitive", "reflexive",
            "symmetrical", "asymmetrical", "hierarchical", "heterarchical",
            "networked", "decentralized", "distributed", "centralized",
        ]
        import random
        random.seed(42)
        text = " ".join(
            " ".join(random.sample(words_pool, min(30, len(words_pool)))) + "."
            for _ in range(100)
        )
        result = estimate_student_level(text)
        assert result.level == StudentLevel.ADVANCED

    def test_whitespace_only_returns_beginner(self):
        result = estimate_student_level("   \n  \t  ")
        assert result.level == StudentLevel.BEGINNER

    def test_repeated_simple_words_low_diversity(self):
        # Low vocabulary diversity despite high word count
        text = ("the cat is on the mat. the cat is big. the cat is happy. "
                "the cat is on the mat. the cat is big. the cat is happy. ") * 20
        result = estimate_student_level(text)
        # Low diversity should keep it beginner/intermediate
        assert result.level in (StudentLevel.BEGINNER, StudentLevel.INTERMEDIATE)


class TestStudentLevelEnum:
    def test_values(self):
        assert StudentLevel.BEGINNER.value == "beginner"
        assert StudentLevel.INTERMEDIATE.value == "intermediate"
        assert StudentLevel.ADVANCED.value == "advanced"

    def test_to_prompt_context_beginner(self):
        ctx = StudentLevel.BEGINNER.to_prompt_context()
        assert "入门" in ctx
        assert "引导和鼓励" in ctx

    def test_to_prompt_context_intermediate(self):
        ctx = StudentLevel.INTERMEDIATE.to_prompt_context()
        assert "进阶" in ctx
        assert "诊断" in ctx

    def test_to_prompt_context_advanced(self):
        ctx = StudentLevel.ADVANCED.to_prompt_context()
        assert "高级" in ctx
        assert "挑战" in ctx


class TestLevelEstimation:
    def test_to_summary_structure(self):
        result = estimate_student_level("A simple test text for checking summary output format.")
        summary = result.to_summary()
        assert "level" in summary
        assert "word_count" in summary
        assert "avg_sentence_length" in summary
        assert "vocabulary_diversity" in summary
        assert "confidence" in summary
        assert summary["level"] in ("beginner", "intermediate", "advanced")

    def test_to_prompt_context_delegates(self):
        result = estimate_student_level("Some text for testing delegation.")
        ctx = result.to_prompt_context()
        assert isinstance(ctx, str)
        assert len(ctx) > 0
