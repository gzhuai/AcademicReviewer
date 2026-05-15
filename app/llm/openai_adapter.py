import httpx
import logging
from app.config import settings
from app.llm.base import LLMAdapter, LLMFactory

logger = logging.getLogger(__name__)

RETRY_COUNT = 3


def _extract_text(response: dict) -> str:
    choices = response.get("choices", [])
    if not choices:
        raise ValueError(f"No choices in response: {response}")
    msg = choices[0].get("message", {})
    content = msg.get("content", "")
    if not content:
        finish = choices[0].get("finish_reason", "")
        if finish == "length":
            logger.warning("Response truncated due to max_tokens limit")
            return ""
        raise ValueError(f"Empty content in response. Finish: {finish}")
    return content


class OpenAIAdapter(LLMAdapter):
    """GPT-5.5 / 兼容 OpenAI API"""

    def __init__(self, api_key: str = "", model: str = "gpt-5.5"):
        self._api_key = api_key or settings.openai_api_key
        self._model = model
        self._base_url = "https://api.openai.com/v1"

    def model_name(self) -> str:
        return self._model

    def provider_name(self) -> str:
        return "openai"

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
                    return _extract_text(resp.json())
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    logger.warning(f"OpenAI call attempt {attempt + 1}/{RETRY_COUNT} failed: {e}")
                    if attempt == RETRY_COUNT - 1:
                        raise
        return ""


LLMFactory.register("openai", OpenAIAdapter)
