"""Unit tests for app/llm/base.py — JSON parsing and factory registry."""

import pytest
from app.llm.base import LLMAdapter, LLMFactory, LLMFactory as Factory


# ── Concrete adapter for testing abstract base ──

class _TestAdapter(LLMAdapter):
    """Minimal concrete implementation for testing the ABC."""

    async def chat(self, system_prompt, user_message, temperature=0.3, max_tokens=4096):
        return '{"score": 7.5}'

    def model_name(self):
        return "test-model"

    def provider_name(self):
        return "test-provider"


@pytest.fixture
def adapter():
    return _TestAdapter()


@pytest.fixture
def clean_factory():
    """Save and restore factory registry state."""
    saved = dict(LLMFactory._registry)
    yield
    LLMFactory._registry = saved


class TestParseJsonResponse:
    def test_clean_json(self, adapter):
        result = adapter._parse_json_response('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_json_with_markdown_fence(self, adapter):
        result = adapter._parse_json_response('```json\n{"a": 1}\n```')
        assert result == {"a": 1}

    def test_json_with_plain_fence(self, adapter):
        result = adapter._parse_json_response('```\n{"b": 2}\n```')
        assert result == {"b": 2}

    def test_json_surrounded_by_text(self, adapter):
        result = adapter._parse_json_response('Here is the result: {"x": 10} and more text.')
        assert result == {"x": 10}

    def test_nested_braces(self, adapter):
        text = 'Output: {"outer": {"inner": "value", "nested": {"deep": true}}} done.'
        result = adapter._parse_json_response(text)
        assert result == {"outer": {"inner": "value", "nested": {"deep": True}}}

    def test_invalid_json(self, adapter):
        result = adapter._parse_json_response("This is not JSON at all.")
        assert result.get("parse_error") is True
        assert "raw_output" in result

    def test_incomplete_json(self, adapter):
        result = adapter._parse_json_response('{"incomplete": ')
        assert result.get("parse_error") is True

    def test_json_array(self, adapter):
        result = adapter._parse_json_response('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_json_with_trailing_comma(self, adapter):
        """Common LLM mistake: trailing comma in JSON object."""
        result = adapter._parse_json_response('{"a": 1, "b": 2,}')
        # Trailing commas are invalid JSON → should fall back
        assert result.get("parse_error") is True

    def test_json_with_single_quotes(self, adapter):
        """LLMs sometimes use single quotes."""
        result = adapter._parse_json_response("{'key': 'value'}")
        assert result.get("parse_error") is True  # single quotes not valid JSON

    def test_chinese_characters_in_json(self, adapter):
        result = adapter._parse_json_response('{"message": "你好", "score": 8.5}')
        assert result == {"message": "你好", "score": 8.5}


class TestChatJson:
    @pytest.mark.asyncio
    async def test_returns_parsed_dict(self, adapter):
        result = await adapter.chat_json("system", "user")
        assert result == {"score": 7.5}


class TestLLMFactory:
    def test_register_and_create(self, clean_factory):
        LLMFactory.register("_test", _TestAdapter)
        adapter = LLMFactory.create("_test")
        assert isinstance(adapter, _TestAdapter)
        assert adapter.model_name() == "test-model"
        assert adapter.provider_name() == "test-provider"

    def test_create_unknown_provider(self, clean_factory):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMFactory.create("nonexistent_provider_xyz")

    def test_create_respects_registry_isolation(self, clean_factory):
        """Each provider key maps to its own class."""
        LLMFactory.register("_test_a", _TestAdapter)

        class _OtherAdapter(_TestAdapter):
            def model_name(self):
                return "other-model"

        LLMFactory.register("_test_b", _OtherAdapter)

        a = LLMFactory.create("_test_a")
        b = LLMFactory.create("_test_b")
        assert a.model_name() == "test-model"
        assert b.model_name() == "other-model"
