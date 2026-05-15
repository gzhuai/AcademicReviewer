from abc import ABC, abstractmethod
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    """所有 LLM 适配器的统一抽象接口"""

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        ...

    @abstractmethod
    def model_name(self) -> str:
        ...

    @abstractmethod
    def provider_name(self) -> str:
        ...

    async def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """调用 LLM 并解析 JSON 响应"""
        response = await self.chat(system_prompt, user_message, temperature, max_tokens)
        return self._parse_json_response(response)

    def _parse_json_response(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse LLM response as JSON, returning raw text")
            return {"raw_output": text, "parse_error": True}


class LLMFactory:
    """根据 provider 名称创建对应的 LLM 适配器"""

    _registry: dict[str, type[LLMAdapter]] = {}

    @classmethod
    def register(cls, provider: str, adapter_cls: type[LLMAdapter]):
        cls._registry[provider] = adapter_cls

    @classmethod
    def create(cls, provider: str, **kwargs) -> LLMAdapter:
        adapter_cls = cls._registry.get(provider)
        if adapter_cls is None:
            raise ValueError(f"Unknown LLM provider: {provider}. Available: {list(cls._registry.keys())}")
        return adapter_cls(**kwargs)
