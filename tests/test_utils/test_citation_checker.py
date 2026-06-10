"""Unit tests for app/utils/citation_checker.py — pure regex logic, no I/O."""

import pytest
from app.utils.citation_checker import (
    extract_cite_keys,
    extract_reference_lines,
    check_citations,
    CitationReport,
    CitationPair,
)


class TestExtractCiteKeys:
    def test_numeric_brackets(self):
        text = "As shown in previous studies [1], the results [2] indicate a strong correlation [4]."
        keys = extract_cite_keys(text)
        assert "1" in keys
        assert "2" in keys
        assert "4" in keys

    def test_numeric_brackets_multi_cite(self):
        """Multi-number brackets like [2,3] are extracted as comma-separated strings
        by the broader author-year patterns, not the numeric bracket pattern."""
        text = "Studies [1,2] and [3] show this effect."
        keys = extract_cite_keys(text)
        # The [3] pattern matches via \[(\d+)\]
        # [1,2] may match via broader patterns
        assert len(keys) >= 1

    def test_author_year_parentheses(self):
        text = "Previous work (Smith, 2020) demonstrated that (Jones and Lee, 2019) effects are significant."
        keys = extract_cite_keys(text)
        assert any("Smith" in k for k in keys)
        assert any("Jones and Lee" in k for k in keys)

    def test_et_al_citations(self):
        text = "Recent findings (Brown et al., 2021) contradict earlier work (Chen et al., 2018)."
        keys = extract_cite_keys(text)
        assert any("Brown" in k for k in keys)
        assert any("Chen" in k for k in keys)

    def test_empty_text(self):
        assert extract_cite_keys("") == []

    def test_no_citations(self):
        text = "This paragraph contains no citations or references at all."
        assert extract_cite_keys(text) == []

    def test_inline_author_year(self):
        text = "According to Wilson et al. (2022), the hypothesis is supported. Garcia (2021) disagrees."
        keys = extract_cite_keys(text)
        assert len(keys) >= 2

    def test_author_year_with_letter_suffix(self):
        text = "See (Johnson, 2019a) and (Johnson, 2019b) for comparison."
        keys = extract_cite_keys(text)
        assert any("2019a" in k for k in keys)
        assert any("2019b" in k for k in keys)


class TestExtractReferenceLines:
    def test_splits_lines(self):
        refs = "Smith, J. (2020). Title. Journal.\n\nJones, K. (2019). Another. Press."
        lines = extract_reference_lines(refs)
        assert len(lines) == 2

    def test_skips_empty_lines(self):
        refs = "\n\nSmith, J. (2020).\n\n\nJones, K. (2019).\n"
        lines = extract_reference_lines(refs)
        assert len(lines) == 2

    def test_empty_string(self):
        assert extract_reference_lines("") == []


class TestCheckCitations:
    def test_all_matched(self):
        text = "See (Smith, 2020) and (Jones, 2019)."
        refs = "Smith, J. (2020). Title. Journal.\nJones, K. (2019). Another. Press."
        report = check_citations(text, refs)
        assert report.match_rate == 1.0
        assert report.matched_count == report.total_cites

    def test_partial_match(self):
        text = "See (Smith, 2020) and (Brown, 2018)."
        refs = "Smith, J. (2020). Title. Journal."
        report = check_citations(text, refs)
        assert report.match_rate < 1.0
        assert len(report.unmatched_cites) > 0

    def test_empty_refs_section(self):
        text = "See (Smith, 2020)."
        report = check_citations(text, "")
        assert report.match_rate == 0.0
        assert len(report.unmatched_cites) == report.total_cites

    def test_no_citations_in_text(self):
        text = "Just a paragraph with no citations."
        refs = "Smith, J. (2020). Something."
        report = check_citations(text, refs)
        assert report.total_cites == 0
        assert report.match_rate == 1.0  # 0/0 = 1.0 by definition

    def test_surname_matching_case_insensitive(self):
        text = "As discussed (SMITH, 2020)."
        refs = "smith, j. (2020). Title."
        report = check_citations(text, refs)
        assert report.match_rate == 1.0

    def test_multiple_authors_matching(self):
        """Surname-based matching: 'Garcia' from cite key matches 'Garcia' in ref."""
        text = "See (Garcia et al., 2021)."
        refs = "Garcia, A., & Martinez, B. (2021). Title. Journal, 10(2), 100-120."
        report = check_citations(text, refs)
        assert report.matched_count >= 1

    def test_citation_report_properties(self, sample_isef_text, sample_refs_section):
        report = check_citations(sample_isef_text, sample_refs_section)
        assert isinstance(report.total_cites, int)
        assert isinstance(report.matched_count, int)
        assert 0.0 <= report.match_rate <= 1.0


class TestCitationReport:
    def test_empty_report(self):
        report = CitationReport()
        assert report.total_cites == 0
        assert report.matched_count == 0
        assert report.match_rate == 1.0

    def test_with_pairs(self):
        p1 = CitationPair(cite_id="[1]", cite_text="[1]", reference_text="Ref 1", is_matched=True)
        p2 = CitationPair(cite_id="[2]", cite_text="[2]", reference_text=None, is_matched=False)
        report = CitationReport(pairs=[p1, p2])
        assert report.total_cites == 2
        assert report.matched_count == 1
        assert report.match_rate == 0.5
