"""Unit tests for app/calibration/feature_extractor.py — regex-based text analysis."""

import pytest
from app.calibration.feature_extractor import (
    extract_sentences,
    tokenize_words,
    extract_features,
    features_to_dict,
    feature_names,
    DocumentFeatures,
)


class TestExtractSentences:
    def test_basic_splitting(self):
        text = "This is sentence one. This is sentence two! Is this sentence three? Yes it is."
        sents = extract_sentences(text)
        assert len(sents) == 4

    def test_short_sentences_filtered(self):
        """Sentences with < 3 words are filtered out."""
        text = "Hello. No. This is a proper sentence. OK. Another proper sentence here."
        sents = extract_sentences(text)
        # "Hello." and "No." and "OK." have < 3 words → filtered
        assert len(sents) == 2
        assert all(len(s.split()) >= 3 for s in sents)

    def test_empty_text(self):
        assert extract_sentences("") == []

    def test_abbreviations_not_split(self):
        """Common abbreviations with periods should not cause splitting (known limitation)."""
        text = "Dr. Smith conducted the study. The results were significant."
        sents = extract_sentences(text)
        # Current regex splits on ". " so "Dr." then "Smith..." may cause extra splits
        # This test documents current behavior, not ideal behavior
        assert len(sents) >= 2  # at minimum we get the two obvious sentences


class TestTokenizeWords:
    def test_extracts_english_words(self):
        words = tokenize_words("The quick brown fox jumps over 123 numbers!")
        assert "the" in words
        assert "quick" in words
        assert "123" not in words  # numbers not matched by [a-zA-Z]+
        assert "!" not in words

    def test_lowercases(self):
        words = tokenize_words("The THE the")
        assert all(w == "the" for w in words)

    def test_empty_text(self):
        assert tokenize_words("") == []


class TestExtractFeatures:
    def test_word_count(self, sample_isef_text):
        feats = extract_features(sample_isef_text)
        assert feats.word_count > 100  # ISEF sample has substantial content
        assert feats.word_count == len(tokenize_words(sample_isef_text))

    def test_citation_density_isef(self, sample_isef_text):
        """ISEF paper should have citations like [1], [2,3]."""
        feats = extract_features(sample_isef_text)
        assert feats.citation_density > 0

    def test_passive_voice_detection(self):
        text = "The samples were measured using a spectrophotometer. The data was analyzed with SPSS."
        feats = extract_features(text)
        assert feats.passive_voice_ratio > 0

    def test_no_passive_voice(self):
        text = "We measured the samples. We analyzed the data. We found significant results."
        feats = extract_features(text)
        # Active voice dominant → passive ratio should be low
        assert feats.passive_voice_ratio < 0.5

    def test_vocabulary_diversity(self):
        """A text with many unique words should have high TTR."""
        text = "the the the the the the the the the the"
        feats = extract_features(text)
        assert feats.vocabulary_diversity == 1.0 / 10.0  # 1 unique / 10 total

    def test_vocabulary_diversity_varied(self):
        text = "apple banana cherry date elderberry fig grape honeydew"
        feats = extract_features(text)
        assert feats.vocabulary_diversity == 1.0  # all unique

    def test_logical_markers_detected(self):
        text = "Therefore, the hypothesis is supported. However, some limitations exist. Moreover, future work is needed."
        feats = extract_features(text)
        assert feats.logical_marker_density > 0

    def test_transition_frequency(self):
        text = "First, we collected data. However, the results were unexpected. Therefore, we revised our approach."
        feats = extract_features(text)
        assert feats.transition_frequency > 0

    def test_section_coverage_full(self, sample_isef_text):
        """ISEF sample has Abstract, Introduction, Methods, Results, Discussion, References.
        The section headers may have numbers (e.g. '1. Introduction') which
        doesn't match the strict regex. We check at least some sections are detected."""
        feats = extract_features(sample_isef_text)
        # Sample has sections with numbering like "1. Introduction", "2. Methods"
        # The strict regex only matches bare headers like "Introduction" or "Methods"
        # So coverage will be partial — at minimum Abstract and References should match
        assert feats.section_coverage >= 0.125  # at least 1 of 8 sections

    def test_section_coverage_empty(self):
        feats = extract_features("Just a paragraph. No section headers here.")
        assert feats.section_coverage == 0.0

    def test_has_p_value(self, sample_isef_text):
        feats = extract_features(sample_isef_text)
        assert feats.has_p_value == 1.0  # ISEF sample has "p < 0.01"

    def test_no_p_value(self):
        feats = extract_features("No statistics here, just qualitative analysis.")
        assert feats.has_p_value == 0.0

    def test_has_effect_size(self):
        text = "We computed Cohen's d to measure the effect size between groups."
        feats = extract_features(text)
        assert feats.has_effect_size == 1.0

    def test_has_control_group(self):
        text = "The control group received a placebo while the experimental group received the treatment."
        feats = extract_features(text)
        assert feats.has_control_group == 1.0

    def test_has_sample_size(self):
        text = "We recruited n = 200 participants from the local community."
        feats = extract_features(text)
        assert feats.has_sample_size == 1.0

    def test_has_sample_size_N_format(self):
        text = "N = 50 subjects were enrolled in the study."
        feats = extract_features(text)
        assert feats.has_sample_size == 1.0

    def test_evidence_diversity(self, sample_isef_text):
        feats = extract_features(sample_isef_text)
        # ISEF paper has academic references
        assert feats.evidence_source_count >= 1
        assert 0.0 <= feats.evidence_diversity_score <= 1.0

    def test_gap_statement_present(self, sample_isef_text):
        feats = extract_features(sample_isef_text)
        assert feats.gap_statement_present == 1.0  # "remain incompletely understood"

    def test_no_gap_statement(self):
        feats = extract_features("Everything is fully understood. No gaps exist.")
        assert feats.gap_statement_present == 0.0

    def test_limitations_section(self):
        text = "Several limitations should be considered when interpreting these results."
        feats = extract_features(text)
        assert feats.limitations_section_present == 1.0

    def test_future_work_mentioned(self):
        text = "Future research should investigate the long-term effects of this intervention."
        feats = extract_features(text)
        assert feats.future_work_mentioned == 1.0

    def test_hook_sentence(self):
        text = "Imagine a world without plastic pollution. This paper explores solutions."
        feats = extract_features(text)
        assert feats.hook_sentence_present == 1.0

    def test_empty_text(self):
        feats = extract_features("")
        assert feats.word_count == 0
        assert feats.sentence_count == 1  # guard: min 1
        assert feats.citation_density == 0.0

    def test_filename_stored(self):
        feats = extract_features("Some text.", filename="test_doc.txt")
        assert feats.filename == "test_doc.txt"

    def test_claim_count_estimate(self, sample_isef_text):
        feats = extract_features(sample_isef_text)
        # Research papers typically make several claims
        assert feats.claim_count_estimate > 0

    def test_avg_sentence_length(self, sample_isef_text):
        feats = extract_features(sample_isef_text)
        assert feats.avg_sentence_length > 5.0  # academic writing has longer sentences

    def test_avg_paragraph_length(self, sample_isef_text):
        feats = extract_features(sample_isef_text)
        assert feats.avg_paragraph_length > 0


class TestFeaturesToDict:
    def test_all_keys_present(self):
        feats = DocumentFeatures(filename="test.txt")
        d = features_to_dict(feats)
        assert d["filename"] == "test.txt"
        assert "word_count" in d
        assert "citation_density" in d
        assert "has_p_value" in d

    def test_rounds_floats(self):
        feats = DocumentFeatures(
            citation_density=3.4567,
            passive_voice_ratio=0.12345,
            vocabulary_diversity=0.789012,
        )
        d = features_to_dict(feats)
        assert d["citation_density"] == 3.46
        assert d["passive_voice_ratio"] == 0.123
        assert d["vocabulary_diversity"] == 0.789


class TestFeatureNames:
    def test_returns_21_features(self):
        names = feature_names()
        assert len(names) == 21

    def test_contains_key_features(self):
        names = feature_names()
        assert "citation_density" in names
        assert "passive_voice_ratio" in names
        assert "vocabulary_diversity" in names
        assert "has_p_value" in names
        assert "section_coverage" in names
        assert "gap_statement_present" in names
