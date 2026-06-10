"""Unit tests for app/utils/doc_parser.py — document parsing logic."""

import tempfile
from pathlib import Path

import pytest
from app.utils.doc_parser import parse_document, ParsedDocument


class TestParseTxt:
    def test_parse_simple_txt(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello world. This is a test document.")
            tmp_path = f.name

        try:
            doc = parse_document(tmp_path)
            assert isinstance(doc, ParsedDocument)
            assert doc.word_count == 7
            assert "Hello world" in doc.text
        finally:
            Path(tmp_path).unlink()

    def test_parse_md_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# Title\n\nThis is markdown content.")
            tmp_path = f.name

        try:
            doc = parse_document(tmp_path)
            assert doc.word_count >= 5
        finally:
            Path(tmp_path).unlink()

    def test_unsupported_format_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jpg", delete=False, encoding="utf-8") as f:
            f.write("not really a jpg")
            tmp_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                parse_document(tmp_path)
        finally:
            Path(tmp_path).unlink()

    def test_metadata_includes_filename(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Test content.")
            tmp_path = f.name

        try:
            doc = parse_document(tmp_path)
            assert doc.metadata["filename"] == Path(tmp_path).name
            assert doc.metadata["format"] == ".txt"
        finally:
            Path(tmp_path).unlink()


class TestParsedDocument:
    def test_paragraphs(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        doc = ParsedDocument(text=text, word_count=6)
        paras = doc.paragraphs
        assert len(paras) == 3
        assert paras[0] == "Paragraph one."

    def test_paragraphs_single(self):
        text = "Just one paragraph."
        doc = ParsedDocument(text=text, word_count=4)
        assert len(doc.paragraphs) == 1

    def test_paragraphs_trims_whitespace(self):
        text = "  Para one.  \n\n  \n\n  Para two.  "
        doc = ParsedDocument(text=text, word_count=4)
        paras = doc.paragraphs
        assert len(paras) == 2
        assert paras[0] == "Para one."

    def test_get_text_chunk(self):
        text = "word1 word2 word3 word4 word5 word6"
        doc = ParsedDocument(text=text, word_count=6)
        chunk = doc.get_text_chunk(max_words=3)
        assert chunk == "word1 word2 word3"

    def test_get_text_chunk_larger_than_text(self):
        text = "short text here"
        doc = ParsedDocument(text=text, word_count=3)
        chunk = doc.get_text_chunk(max_words=100)
        assert chunk == text
