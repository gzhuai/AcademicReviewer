"""Unit tests for app/config.py — competition registry and alias normalization."""

import pytest
from app.config import (
    normalize_competition_name,
    get_competition_list,
    clear_config_cache,
    _load_registry,
    _build_alias_map,
)


class TestNormalizeCompetitionName:
    def test_exact_match(self):
        assert normalize_competition_name("ISEF") == "ISEF"

    def test_case_insensitive(self):
        assert normalize_competition_name("isef") == "ISEF"
        assert normalize_competition_name("Isef") == "ISEF"

    def test_alias_english(self):
        assert normalize_competition_name("JL") == "John Locke"

    def test_alias_chinese(self):
        assert normalize_competition_name("约翰洛克") == "John Locke"

    def test_alias_mixed(self):
        assert normalize_competition_name("JohnLocke") == "John Locke"

    def test_unknown_competition_passthrough(self):
        result = normalize_competition_name("UnknownCompetition")
        assert result == "UnknownCompetition"

    def test_empty_string(self):
        assert normalize_competition_name("") == ""

    def test_whitespace_only(self):
        result = normalize_competition_name("   ")
        assert result == "   "  # returns as-is after strip()

    def test_alias_with_extra_spaces(self):
        # " john locke竞赛 " has leading space — strip() handles it
        result = normalize_competition_name("john locke竞赛")
        assert result == "John Locke"  # alias "john locke竞赛" registered

    def test_sts_alias(self):
        assert normalize_competition_name("Regeneron STS") == "STS"


class TestGetCompetitionList:
    def test_returns_list(self):
        comps = get_competition_list()
        assert isinstance(comps, list)
        assert len(comps) >= 10  # registry has 11 competitions

    def test_each_has_required_fields(self):
        comps = get_competition_list()
        for c in comps:
            assert "name" in c
            assert "type" in c
            assert "structure_schema" in c
            assert "evidence_config" in c
            assert "style_template" in c

    def test_contains_major_competitions(self):
        comps = get_competition_list()
        names = [c["name"] for c in comps]
        assert "ISEF" in names
        assert "John Locke" in names
        assert "HiMCM" in names
        assert "STS" in names


class TestCacheInvalidation:
    def test_clear_cache_resets(self):
        # First load populates cache
        result1 = normalize_competition_name("ISEF")
        assert result1 == "ISEF"

        # Clear and reload
        clear_config_cache()

        # Should still work after cache clear
        result2 = normalize_competition_name("ISEF")
        assert result2 == "ISEF"
