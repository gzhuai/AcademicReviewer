from pathlib import Path

from app.agents.base import BaseAgent

CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"


class ArgumentEvidenceAgent(BaseAgent):
    agent_name = "ArgumentEvidence"
    prompt_template_path = "a3_argument_evidence.txt"
    score_key = "overall_score"

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
        hint = self._load_type_hint(competition_type)
        parts = [
            "请审查以下文稿的论点与证据质量：",
            f"竞赛类型：{competition_type}",
            f"竞赛专项提示：{hint}" if hint else "",
            "",
            "--- 证据标准配置 ---",
            evidence_patterns,
            "",
            "--- 稿件正文 ---",
            document_text,
            "",
            "请输出 JSON。输出中的 validation_point.type 应从以下选取最匹配的：counterargument_analysis / limitation_review / sensitivity_check / alternative_comparison。",
        ]
        return "\n".join(parts)

    @staticmethod
    def _load_type_hint(competition_type: str) -> str:
        """Load competition type hint from JSON config."""
        hints_path = CONFIGS_DIR / "competition_type_hints.json"
        if hints_path.exists():
            import json
            hints = json.loads(hints_path.read_text(encoding="utf-8"))
            entry = hints.get(competition_type, {})
            return entry.get("hint", "")
        return ""

    def _load_evidence_config(self, competition_type: str) -> str:
        config_path = CONFIGS_DIR / "evidence_patterns" / f"{competition_type}.json"
        if config_path.exists():
            import json
            return json.dumps(json.loads(config_path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
        return "{}"
