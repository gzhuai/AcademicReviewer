import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.agents.base import BaseAgent
from app.llm.base import LLMAdapter, LLMFactory
from app.utils.doc_parser import parse_document

logger = logging.getLogger(__name__)

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"

# Default agent weights — used when competition config doesn't specify its own.
DEFAULT_AGENT_WEIGHTS = {
    "RubricParser": 0.25,
    "StructureLogic": 0.20,
    "ArgumentEvidence": 0.25,
    "LanguageStyle": 0.15,
    "AcademicIntegrity": 0.15,
}

REFERENCES_HEADERS = [
    r"^References\s*$",
    r"^Bibliography\s*$",
    r"^Works\s+Cited\s*$",
    r"^Literature\s+Cited\s*$",
]


@dataclass
class ReviewReport:
    submission_id: str = ""
    competition: str = ""
    competition_type: str = ""
    total_score: float | None = None
    scores: dict = field(default_factory=dict)
    rubric: dict | None = None
    structure: dict | None = None
    argument: dict | None = None
    language: dict | None = None
    integrity: dict | None = None
    meta: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


class Orchestrator:
    def __init__(self, llm: LLMAdapter):
        self.llm = llm
        self._agent_cache: dict[str, BaseAgent] = {}

    def _get_agent(self, agent_cls: type[BaseAgent]) -> BaseAgent:
        key = agent_cls.__name__
        if key not in self._agent_cache:
            self._agent_cache[key] = agent_cls(self.llm)
        return self._agent_cache[key]

    def lookup_competition(self, competition_name: str) -> dict:
        from app.config import normalize_competition_name
        registry_path = CONFIGS_DIR / "competition_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))

        canonical = normalize_competition_name(competition_name)
        comp = registry["competitions"].get(canonical)
        if comp:
            return comp

        # Not in registry — warn but don't crash. Use a generic fallback config.
        logger.warning(f"Competition '{competition_name}' not found in registry. Using generic config.")
        return {
            "type": "research",
            "subtype": None,
            "structure_schema": "research.json",
            "evidence_config": "research.json",
            "style_template": "tech_academic.json",
            "citation_style": "APA",
        }

    async def review(self, file_path: str, competition: str) -> ReviewReport:
        t0 = time.perf_counter()

        report = ReviewReport(competition=competition)

        comp_config = self.lookup_competition(competition)
        report.competition_type = comp_config["type"]

        doc = parse_document(file_path)
        logger.info(f"Parsed document: {doc.word_count} words, {competition=}, type={comp_config['type']}")

        rubric_config = self._load_rubric_config(competition)

        from app.agents.rubric_parser import RubricParserAgent
        from app.agents.structure_logic import StructureLogicAgent
        from app.agents.argument_evidence import ArgumentEvidenceAgent

        logger.info("Starting Round 1: A1 (Rubric) + A2 (Structure) + A3 (Argument)")
        evidence_cfg = comp_config.get("evidence_config", comp_config["type"])
        if evidence_cfg.endswith(".json"):
            evidence_cfg = evidence_cfg[:-5]
        r1_tasks = [
            self._get_agent(RubricParserAgent).run(
                rubric_text=json.dumps(rubric_config, ensure_ascii=False),
            ),
            self._get_agent(StructureLogicAgent).run(
                document_text=doc.text,
                competition_type=comp_config["type"],
            ),
            self._get_agent(ArgumentEvidenceAgent).run(
                document_text=doc.text,
                competition_type=evidence_cfg,
            ),
        ]

        r1_results = await asyncio.gather(*r1_tasks, return_exceptions=True)

        for r in r1_results:
            if isinstance(r, Exception):
                report.errors.append(f"Round 1 agent error: {r}")
                logger.error(f"Round 1 agent error: {r}")
                continue
            agent_name = r.get("agent", "")
            if agent_name == "RubricParser":
                report.rubric = r
            elif agent_name == "StructureLogic":
                report.structure = r
            elif agent_name == "ArgumentEvidence":
                report.argument = r

        r1_t = time.perf_counter() - t0
        logger.info(f"Round 1 completed in {r1_t:.1f}s")

        ref_section = self._extract_references_section(doc.text)

        from app.agents.language_style import LanguageStyleAgent
        from app.agents.academic_integrity import AcademicIntegrityAgent

        logger.info("Starting Round 2: A4 (Language) + A5 (Integrity)")

        # Load style guide for A4
        style_guide = self._load_style_guide(comp_config)
        r2_tasks = [
            self._get_agent(LanguageStyleAgent).run(
                document_text=doc.text,
                style_guide=style_guide,
            ),
            self._get_agent(AcademicIntegrityAgent).run(
                document_text=doc.text,
                references_section=ref_section,
                similarity_report="{}",
            ),
        ]

        r2_results = await asyncio.gather(*r2_tasks, return_exceptions=True)

        for r in r2_results:
            if isinstance(r, Exception):
                report.errors.append(f"Round 2 agent error: {r}")
                logger.error(f"Round 2 agent error: {r}")
                continue
            agent_name = r.get("agent", "")
            if agent_name == "LanguageStyle":
                report.language = r
            elif agent_name == "AcademicIntegrity":
                report.integrity = r

        total_elapsed = time.perf_counter() - t0
        report.total_score = self._compute_total_score(report)
        report.meta["duration_seconds"] = round(total_elapsed, 2)
        report.meta["word_count"] = doc.word_count
        report.meta["model"] = self.llm.model_name()
        report.meta["provider"] = self.llm.provider_name()

        # Generate annotated document
        try:
            from app.utils.annotation_builder import build_annotated_markdown
            report.meta["annotated_md"] = build_annotated_markdown(
                original_text=doc.text,
                structure=report.structure,
                argument=report.argument,
                language=report.language,
                integrity=report.integrity,
                rubric=report.rubric,
            )
        except Exception as exc:
            logger.warning(f"Failed to generate annotated document: {exc}")

        logger.info(f"Review completed in {total_elapsed:.1f}s, total_score={report.total_score}")

        try:
            from app.utils.sync import report_review
            from app.config import normalize_competition_name
            await report_review({
                "competition": normalize_competition_name(report.competition),
                "competition_type": report.competition_type,
                "total_score": report.total_score,
                "scores": report.scores,
                "meta": report.meta,
            })
        except Exception:
            pass

        return report

    def _compute_total_score(self, report: ReviewReport) -> float | None:
        from app.agents.rubric_parser import RubricParserAgent
        from app.agents.structure_logic import StructureLogicAgent
        from app.agents.argument_evidence import ArgumentEvidenceAgent
        from app.agents.language_style import LanguageStyleAgent
        from app.agents.academic_integrity import AcademicIntegrityAgent

        # Load competition-specific weights, fall back to defaults
        comp_config = self.lookup_competition(report.competition)
        agent_weights = comp_config.get("agent_weights", DEFAULT_AGENT_WEIGHTS)

        weighted_sum = 0.0
        weight_sum = 0.0

        agent_score_map = [
            (RubricParserAgent, report.rubric),
            (StructureLogicAgent, report.structure),
            (ArgumentEvidenceAgent, report.argument),
            (LanguageStyleAgent, report.language),
            (AcademicIntegrityAgent, report.integrity),
        ]

        for agent_cls, result in agent_score_map:
            if result is None:
                continue
            score = self._extract_numeric_score(result, agent_cls.score_key)
            if score is not None:
                weight = agent_weights.get(agent_cls.agent_name, 0.0)
                weighted_sum += score * weight
                weight_sum += weight
                report.scores[agent_cls.agent_name] = round(score, 1)

        if weight_sum == 0:
            return None
        return round(weighted_sum / weight_sum, 1)

    @staticmethod
    def _extract_numeric_score(result: dict, key: str) -> float | None:
        val = result.get(key)
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _load_rubric_config(self, competition: str) -> dict:
        safe_name = competition.lower().replace(" ", "_").replace("-", "_")
        # Prevent path traversal: only use the basename portion
        safe_name = Path(safe_name).name
        rubric_path = CONFIGS_DIR / "rubrics" / f"{safe_name}_2026.json"
        if not rubric_path.exists():
            rubric_path = CONFIGS_DIR / "rubrics" / "isef_2026.json"
        return json.loads(rubric_path.read_text(encoding="utf-8"))

    @staticmethod
    def _load_style_guide(comp_config: dict) -> dict:
        """Load the style guide JSON for the competition type, or return empty dict."""
        style_template = comp_config.get("style_template", "")
        if not style_template:
            return {}
        style_path = CONFIGS_DIR / "style_guides" / style_template
        if style_path.exists():
            return json.loads(style_path.read_text(encoding="utf-8"))
        return {}

    @staticmethod
    def _extract_references_section(text: str) -> str:
        for header_pattern in REFERENCES_HEADERS:
            match = re.search(rf"(?:^|\n){header_pattern}\s*\n", text, re.MULTILINE | re.IGNORECASE)
            if match:
                start = match.end()
                remaining = text[start:]
                next_section = re.search(
                    r"\n\s*(?:Appendix|Acknowledgments?|Appendices|Supplementary)\s*\n",
                    remaining,
                    re.IGNORECASE | re.MULTILINE,
                )
                if next_section:
                    return remaining[: next_section.start()].strip()
                return remaining.strip()
        return ""
