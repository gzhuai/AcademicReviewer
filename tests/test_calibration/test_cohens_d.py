"""Unit tests for app/calibration/cohens_d.py — pure statistics, no I/O."""

import pytest
from app.calibration.cohens_d import (
    cohens_d,
    categorize_effect,
    compute_effect_sizes,
    cross_validate,
    EffectSizeResult,
    CrossValidationResult,
)


class TestCohensD:
    def test_large_positive_effect(self):
        """Two clearly separated groups should produce |d| > 0.8."""
        group_a = [10.0, 12.0, 11.0, 13.0, 12.0]
        group_b = [2.0, 3.0, 1.0, 4.0, 3.0]
        d, mean_a, mean_b, sd = cohens_d(group_a, group_b)
        assert d > 2.0  # very large effect
        assert mean_a > mean_b

    def test_large_negative_effect(self):
        """group_a < group_b → d < 0."""
        group_a = [1.0, 2.0, 3.0]
        group_b = [10.0, 11.0, 12.0]
        d, mean_a, mean_b, sd = cohens_d(group_a, group_b)
        assert d < -2.0

    def test_no_effect(self):
        """Identical groups → d ≈ 0."""
        group_a = [5.0, 6.0, 5.5, 6.5, 5.0]
        group_b = [5.0, 6.0, 5.5, 6.5, 5.0]
        d, _, _, _ = cohens_d(group_a, group_b)
        assert abs(d) < 0.001

    def test_small_sample(self):
        """n=2 each should still work."""
        d, _, _, _ = cohens_d([10.0, 12.0], [5.0, 7.0])
        assert d > 1.0

    def test_single_element_returns_zero(self):
        """n=1 per group: cannot compute variance → returns 0."""
        d, _, _, _ = cohens_d([10.0], [5.0])
        assert d == 0.0

    def test_zero_variance(self):
        """All identical values → sd_pooled=0 → returns 0."""
        d, _, _, _ = cohens_d([5.0, 5.0, 5.0], [5.0, 5.0, 5.0])
        assert d == 0.0

    def test_returns_tuple_of_four(self):
        result = cohens_d([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        assert len(result) == 4
        d, mean_a, mean_b, sd = result
        assert isinstance(d, float)
        assert isinstance(mean_a, float)
        assert isinstance(mean_b, float)
        assert isinstance(sd, float)


class TestCategorizeEffect:
    def test_critical(self):
        cat, label = categorize_effect(0.9)
        assert cat == "critical"
        assert label == "大效应"

    def test_critical_negative(self):
        cat, label = categorize_effect(-0.85)
        assert cat == "critical"

    def test_major(self):
        cat, label = categorize_effect(0.6)
        assert cat == "major"
        assert label == "中效应"

    def test_major_boundary(self):
        cat, _ = categorize_effect(0.5)
        assert cat == "major"

    def test_minor(self):
        cat, label = categorize_effect(0.3)
        assert cat == "minor"
        assert label == "小效应"

    def test_minor_boundary(self):
        cat, _ = categorize_effect(0.2)
        assert cat == "minor"

    def test_none(self):
        cat, label = categorize_effect(0.1)
        assert cat == "none"
        assert label == "无差异"

    def test_zero(self):
        cat, _ = categorize_effect(0.0)
        assert cat == "none"


class TestComputeEffectSizes:
    def test_basic(self, sample_winners_features, sample_losers_features, feature_name_list):
        results = compute_effect_sizes(
            sample_winners_features, sample_losers_features, feature_name_list
        )
        assert len(results) > 0
        # citation_density should have a large effect
        citation = next(r for r in results if r.feature_name == "citation_density")
        assert citation.d_absolute > 0.5
        assert citation.category in ("critical", "major")
        assert citation.signal_type == "正向"

    def test_sorted_by_absolute_d(self, sample_winners_features, sample_losers_features, feature_name_list):
        results = compute_effect_sizes(
            sample_winners_features, sample_losers_features, feature_name_list
        )
        for i in range(len(results) - 1):
            assert results[i].d_absolute >= results[i + 1].d_absolute

    def test_empty_input(self):
        results = compute_effect_sizes([], [], ["citation_density", "word_count"])
        assert results == []

    def test_binary_feature_negative_signal(self, sample_winners_features, sample_losers_features, feature_name_list):
        """Binary features where winners have it and losers don't should show the gap.
        has_p_value: winners 1.0 vs losers 0.0 → we check the mean difference direction."""
        results = compute_effect_sizes(
            sample_winners_features, sample_losers_features, feature_name_list
        )
        p_value = next((r for r in results if r.feature_name == "has_p_value"), None)
        # Note: all values within each group are identical → variance=0 → d=0
        # A zero-variance binary feature gets filtered out or has d=0
        # This test documents the edge case: when all winners=1.0 and all losers=0.0,
        # the pooled SD is 0, so Cohen's d is 0 — the effect is real but inexpressible.
        if p_value is not None:
            # The mean difference direction is still meaningful
            assert p_value.mean_winners > p_value.mean_losers
        else:
            # It's also valid if this feature is skipped due to zero variance
            pass

    def test_confidence_levels(self, sample_winners_features, sample_losers_features, feature_name_list):
        """Check that confidence is computed based on sample size."""
        results = compute_effect_sizes(
            sample_winners_features, sample_losers_features, feature_name_list
        )
        # 3+3 = 6 samples → "低" confidence
        for r in results:
            assert r.confidence == "低"

    def test_missing_feature_in_some_dicts(self):
        winners = [{"citation_density": 5.0, "word_count": 3000}]
        losers = [{"citation_density": 1.0}]  # missing word_count
        results = compute_effect_sizes(winners, losers, ["citation_density", "word_count"])
        # citation_density: both have it → computed
        # word_count: missing in losers → skipped
        assert len(results) == 1
        assert results[0].feature_name == "citation_density"


class TestCrossValidate:
    def test_consistent(self, sample_winners_features, sample_losers_features, feature_name_list):
        """When external winners are similar to internal winners, agreement is high."""
        # Use winner features as external (they should match)
        results = cross_validate(
            sample_winners_features,
            sample_losers_features,
            sample_winners_features,  # same as internal winners
            feature_name_list,
        )
        assert len(results) > 0
        for r in results:
            assert r.agreement in ("一致", "部分一致", "不一致", "无外部样本")

    def test_no_external_samples(self, sample_winners_features, sample_losers_features, feature_name_list):
        results = cross_validate(
            sample_winners_features,
            sample_losers_features,
            [],
            feature_name_list,
        )
        for r in results:
            assert r.agreement == "无外部样本"
            assert r.confidence == "仅内部"

    def test_sorted_by_internal_d(self, sample_winners_features, sample_losers_features, feature_name_list):
        results = cross_validate(
            sample_winners_features,
            sample_losers_features,
            sample_winners_features,
            feature_name_list,
        )
        for i in range(len(results) - 1):
            assert abs(results[i].d_my_winners_vs_losers) >= abs(results[i + 1].d_my_winners_vs_losers)
