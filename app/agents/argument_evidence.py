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
        type_hints = {
            "research": "科研型论文。检查 hypothesis 可验证性、p值/效应量、控制组、统计检验、局限性讨论。不需要检查 counterargument/rebuttal。",
            "research_advanced": "进阶科研型。除科研型检查外，还需检查理论贡献度和方法原创性。",
            "math_modeling": "数学建模论文。检查模型假设合理性、求解路径可追溯、灵敏度分析、公式正确性。不需要检查 counterargument/rebuttal。",
            "discursive": "思辨型议论文。检查 counterargument 质量、rebuttal 强度、逻辑链完整性、哲学引用深度。",
            "social_science": "社科型论文。检查调研方法论、案例深度、跨文化视角。",
            "history": "历史型论文。检查一手史料引用、史学视角、时代语境还原。",
            "finance": "金融投资报告。检查估值模型假设、数据来源可溯性、风险分析、图表准确性。不需要检查 counterargument/rebuttal。",
            "business_case": "商科案例报告。检查 SWOT/PEST/五力框架应用、方案可行性、ROI 计算。需要检查 alternative solutions 对比而非 counterargument。",
        }
        hint = type_hints.get(competition_type, "")
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

    def _load_evidence_config(self, competition_type: str) -> str:
        config_path = CONFIGS_DIR / "evidence_patterns" / f"{competition_type}.json"
        if config_path.exists():
            import json
            return json.dumps(json.loads(config_path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
        return "{}"
