import json
import logging
import time
from pathlib import Path
from app.llm.base import LLMAdapter

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


class BaseAgent:
    agent_name: str = "base"
    prompt_template_path: str = ""

    def __init__(self, llm: LLMAdapter):
        self.llm = llm
        self.template = self._load_prompt() if self.prompt_template_path else ""

    def _load_prompt(self) -> str:
        path = PROMPTS_DIR / self.prompt_template_path
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning(f"Prompt template not found: {path}")
        return ""

    async def run(self, **kwargs) -> dict:
        system_prompt = self._build_system_prompt(**kwargs)
        user_message = self._build_user_message(**kwargs)

        t0 = time.perf_counter()
        try:
            result = await self.llm.chat_json(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.2,
                max_tokens=4096,
            )
        except Exception as e:
            logger.error(f"[{self.agent_name}] LLM call failed: {e}")
            return {"error": str(e), "agent": self.agent_name}

        elapsed = time.perf_counter() - t0
        logger.info(f"[{self.agent_name}] completed in {elapsed:.1f}s")

        return {
            "agent": self.agent_name,
            "model": self.llm.model_name(),
            "provider": self.llm.provider_name(),
            "duration_seconds": round(elapsed, 2),
            **result,
        }

    def _build_system_prompt(self, **kwargs) -> str:
        return self.template

    def _build_user_message(self, **kwargs) -> str:
        return json.dumps(kwargs, ensure_ascii=False)

    @staticmethod
    def _load_json(file_path: str | Path) -> dict:
        path = Path(file_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent.parent.parent / path
        if not path.exists():
            logger.warning(f"Config file not found: {path}")
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
