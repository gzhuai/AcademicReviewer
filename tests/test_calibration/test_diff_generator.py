"""Unit tests for app/calibration/diff_generator.py — config change generation."""

import pytest
from app.calibration.diff_generator import (
    ConfigChange,
    generate_rule_updates,
    generate_fatal_defect_updates,
    diff_configs,
    _get_nested_value,
)
from app.calibration.cohens_d import EffectSizeResult


class TestGetNestedValue:
    def test_simple_key(self):
        data = {"a": 1, "b": 2}
        assert _get_nested_value(data, "a") == 1

    def test_nested_path(self):
        data = {"level1": {"level2": {"level3": "deep"}}}
        assert _get_nested_value(data, "level1.level2.level3") == "deep"

    def test_missing_key(self):
        data = {"a": 1}
        assert _get_nested_value(data, "nonexistent") is None

    def test_missing_intermediate(self):
        data = {"a": 1}
        assert _get_nested_value(data, "a.b.c") is None

    def test_non_dict_intermediate(self):
        data = {"a": "not_a_dict"}
        assert _get_nested_value(data, "a.b") is None


def _make_effect(feature_name, d_value, category="major", signal_type="正向",
                 mean_w=5.0, mean_l=2.0, sd=1.5, confidence="中"):
    return EffectSizeResult(
        feature_name=feature_name,
        d_value=d_value,
        d_absolute=abs(d_value),
        category=category,
        label="中效应" if category == "major" else "大效应",
        mean_winners=mean_w,
        mean_losers=mean_l,
        sd_pooled=sd,
        confidence=confidence,
        signal_type=signal_type,
    )


class TestGenerateRuleUpdates:
    def test_critical_effect_generates_change(self):
        effects = [_make_effect("citation_density", 1.2, category="critical")]
        mapping = {"citation_density": "evidence_standards.min_total_citations"}
        config = {"evidence_standards": {"min_total_citations": 3}}

        changes = generate_rule_updates(effects, ["citation_density"], mapping, config)
        assert len(changes) == 1
        assert changes[0].change_type in ("参数调整", "新增")
        assert changes[0].path == "evidence_standards.min_total_citations"

    def test_none_effect_skipped(self):
        effects = [_make_effect("word_count", 0.1, category="none")]
        mapping = {"word_count": "length.min_words"}
        config = {}

        changes = generate_rule_updates(effects, ["word_count"], mapping, config)
        assert len(changes) == 0

    def test_unknown_feature_skipped(self):
        effects = [_make_effect("citation_density", 1.0, category="critical")]
        mapping = {}  # empty mapping
        config = {}

        changes = generate_rule_updates(effects, ["citation_density"], mapping, config)
        assert len(changes) == 0

    def test_new_config_key(self):
        """When the config path doesn't exist in current_config, change_type should be '新增'."""
        effects = [_make_effect("passive_voice_ratio", -0.9, category="major")]
        mapping = {"passive_voice_ratio": "style_passive_ratio.max_passive_ratio"}
        config = {}  # empty config

        changes = generate_rule_updates(effects, ["passive_voice_ratio"], mapping, config)
        assert len(changes) == 1
        assert changes[0].change_type == "新增"

    def test_multiple_effects(self):
        effects = [
            _make_effect("citation_density", 1.5, category="critical"),
            _make_effect("passive_voice_ratio", -0.8, category="critical"),
            _make_effect("word_count", 0.1, category="none"),  # should be skipped
        ]
        mapping = {
            "citation_density": "evidence.min_cites",
            "passive_voice_ratio": "style.max_passive",
        }
        config = {"evidence": {"min_cites": 2}, "style": {"max_passive": 0.3}}

        changes = generate_rule_updates(effects, ["citation_density", "passive_voice_ratio", "word_count"], mapping, config)
        assert len(changes) == 2


class TestGenerateFatalDefectUpdates:
    def test_binary_feature_negative_critical(self):
        effects = [_make_effect("has_p_value", -1.0, category="critical", signal_type="负向")]
        losers = [{"has_p_value": 0.0}, {"has_p_value": 0.0}, {"has_p_value": 0.0}]
        winners = [{"has_p_value": 1.0}, {"has_p_value": 1.0}, {"has_p_value": 1.0}]
        config = {}

        changes = generate_fatal_defect_updates(effects, losers, winners, config)
        assert len(changes) == 1
        assert "missing_has_p_value" in changes[0].path
        assert changes[0].change_type == "新增 fatal_defect"

    def test_not_binary_feature_skipped(self):
        effects = [_make_effect("citation_density", -1.0, category="critical", signal_type="负向")]
        losers = [{"citation_density": 0.5}]
        winners = [{"citation_density": 5.0}]
        config = {}

        changes = generate_fatal_defect_updates(effects, losers, winners, config)
        assert len(changes) == 0  # citation_density is not in binary_features

    def test_positive_signal_skipped(self):
        effects = [_make_effect("has_p_value", 1.0, category="critical", signal_type="正向")]
        losers = [{"has_p_value": 0.0}]
        winners = [{"has_p_value": 1.0}]
        config = {}

        changes = generate_fatal_defect_updates(effects, losers, winners, config)
        assert len(changes) == 0  # not negative signal

    def test_minor_category_skipped(self):
        effects = [_make_effect("has_control_group", -0.3, category="minor", signal_type="负向")]
        losers = [{"has_control_group": 0.0}]
        winners = [{"has_control_group": 1.0}]
        config = {}

        changes = generate_fatal_defect_updates(effects, losers, winners, config)
        assert len(changes) == 0  # category is minor, not critical/major

    def test_low_winner_loser_gap_skipped(self):
        """If the gap between loser rate and winner rate is <= 0.15, skip."""
        effects = [_make_effect("has_p_value", -0.1, category="critical", signal_type="负向")]
        # Both have similar rates → gap < 0.15
        losers = [{"has_p_value": 1.0}, {"has_p_value": 1.0}]  # 0% missing
        winners = [{"has_p_value": 1.0}, {"has_p_value": 1.0}]  # 0% missing
        config = {}

        changes = generate_fatal_defect_updates(effects, losers, winners, config)
        assert len(changes) == 0


class TestDiffConfigs:
    def test_added_key(self):
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        diffs = diff_configs(old, new)
        assert len(diffs) == 1
        assert diffs[0]["type"] == "新增键"

    def test_removed_key(self):
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        diffs = diff_configs(old, new)
        assert len(diffs) == 1
        assert diffs[0]["type"] == "删除键"

    def test_changed_value(self):
        old = {"a": 1}
        new = {"a": 2}
        diffs = diff_configs(old, new)
        assert len(diffs) == 1
        assert diffs[0]["type"] == "值变更"

    def test_nested_change(self):
        old = {"level1": {"level2": "old_value"}}
        new = {"level1": {"level2": "new_value"}}
        diffs = diff_configs(old, new)
        assert len(diffs) == 1
        assert diffs[0]["path"] == "level1.level2"

    def test_identical_configs(self):
        config = {"a": 1, "b": {"c": 2}}
        diffs = diff_configs(config, config)
        assert diffs == []

    def test_list_element_added(self):
        old = {"items": [1, 2]}
        new = {"items": [1, 2, 3]}
        diffs = diff_configs(old, new)
        assert any(d["type"] == "新增元素" for d in diffs)

    def test_complex_nested_diff(self):
        old = {"section_a": {"key_x": 10}, "section_b": {"key_y": 20}}
        new = {"section_a": {"key_x": 10, "key_z": 30}, "section_c": {"key_w": 40}}
        diffs = diff_configs(old, new)
        # section_b removed, section_c added, key_z added to section_a
        assert len(diffs) >= 2
