import httpx
import logging
from app.config import settings
from app.llm.base import LLMAdapter, LLMFactory

logger = logging.getLogger(__name__)

RETRY_COUNT = 3


class GeminiAdapter(LLMAdapter):
    """Gemini 3.1"""

    def __init__(self, api_key: str = "", model: str = "gemini-3.1-pro"):
        self._api_key = api_key or settings.gemini_api_key
        self._model = model
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    def model_name(self) -> str:
        return self._model

    def provider_name(self) -> str:
        return "gemini"

    async def chat(self, system_prompt: str, user_message: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"[System Instruction]\n{system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": user_message}]})

        async with httpx.AsyncClient(timeout=120) as client:
            for attempt in range(RETRY_COUNT):
                try:
                    resp = await client.post(
                        f"{self._base_url}/models/{self._model}:generateContent",
                        params={"key": self._api_key},
                        headers={"Content-Type": "application/json"},
                        json={
                            "contents": contents,
                            "generationConfig": {
                                "temperature": temperature,
                                "maxOutputTokens": max_tokens,
                            },
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError(f"No candidates in response: {data}")
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        raise ValueError(f"No parts in candidate: {candidates[0]}")
                    return parts[0].get("text", "")
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    logger.warning(f"Gemini call attempt {attempt + 1}/{RETRY_COUNT} failed: {e}")
                    if attempt == RETRY_COUNT - 1:
                        raise
        return ""


LLMFactory.register("gemini", GeminiAdapter)
