from app.agents.base import BaseAgent


class LanguageStyleAgent(BaseAgent):
    agent_name = "LanguageStyle"
    prompt_template_path = "a4_language_style.txt"

    async def run(self, document_text: str = "", style_guide: dict | None = None, **kwargs) -> dict:
        style_context = ""
        if style_guide:
            import json
            style_context = json.dumps(style_guide, ensure_ascii=False, indent=2)

        result = await super().run(
            document_text=document_text,
            style_guide_context=style_context,
            **kwargs,
        )
        return result

    def _build_user_message(self, document_text: str = "", style_guide_context: str = "", **kwargs) -> str:
        parts = ["请审查以下英文稿件的语言与风格：", "", "--- 稿件正文 ---", document_text]
        if style_guide_context:
            parts.extend(["", "--- 风格指南 ---", style_guide_context])
        parts.extend(["", "请输出 JSON，严格遵循 [REWRITE] 和 [SUGGEST] 的分区规则。"])
        return "\n".join(parts)
