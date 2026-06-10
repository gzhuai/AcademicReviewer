from pathlib import Path

from app.agents.base import BaseAgent

CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"


class StructureLogicAgent(BaseAgent):
    agent_name = "StructureLogic"
    prompt_template_path = "a2_structure_logic.txt"
    score_key = "structure_score"

    async def run(self, document_text: str = "", competition_type: str = "", **kwargs) -> dict:
        schema = self._load_structure_schema(competition_type)
        result = await super().run(
            document_text=document_text,
            structure_schema=schema,
            competition_type=competition_type,
            **kwargs,
        )
        return result

    def _build_user_message(self, document_text: str = "", structure_schema: str = "", competition_type: str = "", **kwargs) -> str:
        parts = [
            "请审查以下文稿的结构与逻辑质量：",
            f"竞赛类型：{competition_type}",
            "",
            "--- 结构 Schema ---",
            structure_schema,
            "",
            "--- 稿件正文 ---",
            document_text,
            "",
            "请输出 JSON。",
        ]
        return "\n".join(parts)

    def _load_structure_schema(self, competition_type: str) -> str:
        schema_path = CONFIGS_DIR / "structure_schemas" / f"{competition_type}.json"
        if schema_path.exists():
            import json
            return json.dumps(json.loads(schema_path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
        return "{}"
