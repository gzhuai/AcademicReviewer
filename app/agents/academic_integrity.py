import json
import logging
from pathlib import Path

from app.agents.base import BaseAgent
from app.utils.citation_checker import check_citations

logger = logging.getLogger(__name__)

CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"


class AcademicIntegrityAgent(BaseAgent):
    agent_name = "AcademicIntegrity"
    prompt_template_path = "a5_academic_integrity.txt"
    score_key = "integrity_score"

    async def run(
        self,
        document_text: str = "",
        references_section: str = "",
        similarity_report: str = "",
        submission_id: str = "",
        run_originality_check: bool = True,
        **kwargs,
    ) -> dict:
        citation_report = check_citations(document_text, references_section)

        citation_preprocessed = {
            "total_cites": citation_report.total_cites,
            "matched": citation_report.matched_count,
            "unmatched_cites": citation_report.unmatched_cites,
            "unmatched_refs": citation_report.unmatched_refs,
            "match_rate": round(citation_report.match_rate, 2),
            "format_issues": citation_report.format_issues,
        }

        if run_originality_check and not similarity_report:
            try:
                from app.utils.vector_store import check_originality, collection_count
                corpus_count = collection_count()
                if corpus_count > 0:
                    logger.info(f"Running originality check against {corpus_count} indexed chunks")
                    originality = check_originality(document_text)
                    similarity_report = json.dumps(originality, ensure_ascii=False, indent=2)
                    logger.info(f"Originality score: {originality['originality_score']}/10")
                else:
                    logger.info("ChromaDB corpus is empty, skipping originality check")
                    similarity_report = "{}"
            except Exception as e:
                logger.warning(f"ChromaDB originality check failed: {e}")
                similarity_report = "{}"

        result = await super().run(
            document_text=document_text,
            citation_preprocessed=json.dumps(citation_preprocessed, ensure_ascii=False, indent=2),
            similarity_report=similarity_report if similarity_report else "{}",
            **kwargs,
        )
        return result

    def _build_user_message(
        self,
        document_text: str = "",
        citation_preprocessed: str = "",
        similarity_report: str = "",
        **kwargs,
    ) -> str:
        parts = [
            "请审查以下文稿的学术诚信：",
            "",
            "--- 引文预检结果（规则引擎） ---",
            citation_preprocessed,
            "",
            "--- 相似度报告 ---",
            similarity_report,
            "",
            "--- 稿件正文 ---",
            document_text,
            "",
            "请输出 JSON，融合规则引擎的 citation 结果和你的 AI 审查判断。",
        ]
        return "\n".join(parts)
