import httpx
import logging
from app.config import settings
from app.llm.base import LLMAdapter, LLMFactory

logger = logging.getLogger(__name__)

RETRY_COUNT = 3


class DeepSeekAdapter(LLMAdapter):
    """DeepSeek v4 Pro（兼容 OpenAI API 格式）"""

    def __init__(self, api_key: str = "", model: str = "deepseek-chat"):
        self._api_key = api_key or settings.deepseek_api_key
        self._model = model
        self._base_url = "https://api.deepseek.com/v1"

    def model_name(self) -> str:
        return self._model

    def provider_name(self) -> str:
        return "deepseek"

    async def chat(self, system_prompt: str, user_message: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            for attempt in range(RETRY_COUNT):
                try:
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self._model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message},
                            ],
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise ValueError(f"No choices in response: {data}")
                    return choices[0].get("message", {}).get("content", "")
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    logger.warning(f"DeepSeek call attempt {attempt + 1}/{RETRY_COUNT} failed: {e}")
                    if attempt == RETRY_COUNT - 1:
                        raise
        return ""


LLMFactory.register("deepseek", DeepSeekAdapter)
