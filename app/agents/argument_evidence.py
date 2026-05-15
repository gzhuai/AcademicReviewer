from pathlib import Path

from app.agents.base import BaseAgent

CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"


class ArgumentEvidenceAgent(BaseAgent):
    agent_name = "ArgumentEvidence"
    prompt_template_path = "a3_argument_evidence.txt"

    async def run(self, document_text: str = "", competition_type: str = "", **kwargs) -> dict:
        evidence_config = self._load_evidence_config(competition_type)
        result = await super().run(
            document_text=document_text,
            evidence_patterns=evidence_config,
            competition_type=competition_type,
            **kwargs,
        )
        return result

    def _build_user_message(self, document_text: str = "", evidence_patterns: str = "", competition_type: str = "", **kwargs) -> str:
        parts = [
            "请审查以下文稿的论点与证据质量：",
            f"竞赛类型：{competition_type}",
            "",
            "--- 证据标准配置 ---",
            evidence_patterns,
            "",
            "--- 稿件正文 ---",
            document_text,
            "",
            "请输出 JSON。",
        ]
        return "\n".join(parts)

    def _load_evidence_config(self, competition_type: str) -> str:
        config_path = CONFIGS_DIR / "evidence_patterns" / f"{competition_type}.json"
        if config_path.exists():
            import json
            return json.dumps(json.loads(config_path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
        return "{}"
