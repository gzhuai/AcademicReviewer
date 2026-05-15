from app.agents.base import BaseAgent


class RubricParserAgent(BaseAgent):
    agent_name = "RubricParser"
    prompt_template_path = "a1_rubric_parser.txt"

    async def run(self, rubric_text: str = "", rubric_file: str = "", **kwargs) -> dict:
        if rubric_file:
            rubric_text = self._load_rubric_file(rubric_file)

        return await super().run(rubric_text=rubric_text, **kwargs)

    def _build_user_message(self, rubric_text: str = "", **kwargs) -> str:
        return f"请解析以下竞赛评分标准：\n\n{rubric_text}"

    def _load_rubric_file(self, file_path: str) -> str:
        from pathlib import Path
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Rubric file not found: {file_path}")
        return path.read_text(encoding="utf-8", errors="replace")
