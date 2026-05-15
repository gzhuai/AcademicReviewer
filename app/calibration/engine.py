import json
import logging
from pathlib import Path

from app.calibration.feature_extractor import extract_features, features_to_dict, feature_names
from app.calibration.cohens_d import compute_effect_sizes, cross_validate
from app.calibration.diff_generator import (
    generate_rule_updates,
    generate_fatal_defect_updates,
    diff_configs,
)
from app.calibration.report_generator import generate_calibration_report
from app.calibration.expert_annotator import merge_insights, insights_report_markdown, unify_parse

logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIGS_DIR = BASE_DIR / "configs"
CALIBRATION_DATA_DIR = BASE_DIR / "data" / "calibration"


FEATURE_TO_CONFIG_MAP = {
    "citation_density": "evidence_standards.min_total_citations",
    "passive_voice_ratio": "style_passive_ratio.max_passive_ratio",
    "vocabulary_diversity": "style_vocabulary.min_ttr",
    "logical_marker_density": "style_transitions.min_logical_markers_per_1000w",
    "transition_frequency": "style_transitions.min_transitions_per_1000w",
    "avg_sentence_length": "style_sentence.avg_sentence_length",
    "sentence_length_std": "style_sentence.max_std",
    "section_coverage": "required_sections.coverage_ratio",
    "has_p_value": "quantitative_requirements.expects_p_value",
    "has_effect_size": "quantitative_requirements.expects_effect_size",
    "has_control_group": "quantitative_requirements.expects_control_group",
    "has_sample_size": "quantitative_requirements.expects_sample_size_justification",
    "evidence_diversity_score": "evidence_standards.min_source_types",
    "gap_statement_present": "logic_checks.gap_statement_required",
    "limitations_section_present": "logic_checks.limitations_required",
    "future_work_mentioned": "logic_checks.future_work_required",
}


def _find_compatible_config_files(competition_type: str) -> dict[str, Path]:
    candidates = {}

    rubric_path = CONFIGS_DIR / "rubrics"
    if rubric_path.exists():
        for f in rubric_path.glob("*.json"):
            candidates.setdefault("rubric", f)

    evidence_patterns_path = CONFIGS_DIR / "evidence_patterns" / f"{competition_type}.json"
    if evidence_patterns_path.exists():
        candidates["evidence_patterns"] = evidence_patterns_path

    structure_schemas_path = CONFIGS_DIR / "structure_schemas" / f"{competition_type}.json"
    if structure_schemas_path.exists():
        candidates["structure_schemas"] = structure_schemas_path

    return candidates


def run_calibration(
    competition: str,
    competition_type: str,
    winner_files: list[str],
    loser_files: list[str],
    external_winner_files: list[str] | None = None,
    expert_doc_paths: list[str] | None = None,
    output_report_path: str | None = None,
) -> str:
    external_winner_files = external_winner_files or []
    expert_doc_paths = expert_doc_paths or []

    logger.info(
        f"Starting calibration: {competition=}, {competition_type=}, "
        f"W={len(winner_files)}, L={len(loser_files)}, Ext={len(external_winner_files)}, "
        f"ExpertDocs={len(expert_doc_paths)}"
    )

    logger.info("Step 1/5: Extracting features from all documents...")
    winners_features = []
    for fp in winner_files:
        text = Path(fp).read_text(encoding="utf-8", errors="replace")
        feats = extract_features(text, filename=Path(fp).name)
        winners_features.append(features_to_dict(feats))

    losers_features = []
    for fp in loser_files:
        text = Path(fp).read_text(encoding="utf-8", errors="replace")
        feats = extract_features(text, filename=Path(fp).name)
        losers_features.append(features_to_dict(feats))

    external_features = []
    for fp in external_winner_files:
        text = Path(fp).read_text(encoding="utf-8", errors="replace")
        feats = extract_features(text, filename=Path(fp).name)
        external_features.append(features_to_dict(feats))

    logger.info(f"Features extracted: {len(winners_features)}W + {len(losers_features)}L + {len(external_features)}Ext")

    logger.info("Step 2/5: Computing Cohen's d effect sizes...")
    fnames = feature_names()
    effect_sizes = compute_effect_sizes(winners_features, losers_features, fnames)

    logger.info("Step 3/5: Cross-validation against external winners...")
    cross_validations = cross_validate(
        winners_features, losers_features, external_features, fnames
    ) if external_features else []

    logger.info("Step 4/5: Generating config change suggestions...")
    config_files = _find_compatible_config_files(competition_type)
    current_config = {}
    for cfg_type, cfg_path in config_files.items():
        try:
            current_config[cfg_type] = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            current_config[cfg_type] = {}

    config_changes = []

    for cfg_type, cfg_data in current_config.items():
        changes = generate_rule_updates(
            effect_sizes, fnames, FEATURE_TO_CONFIG_MAP, cfg_data
        )
        for c in changes:
            c.path = f"{cfg_type}.{c.path}"
        config_changes.extend(changes)

        fatal_changes = generate_fatal_defect_updates(
            effect_sizes, losers_features, winners_features, cfg_data
        )
        for c in fatal_changes:
            c.path = f"{cfg_type}.{c.path}"
        config_changes.extend(fatal_changes)

    config_diff = []
    old_config = current_config.get("evidence_patterns", current_config.copy())
    config_diff = diff_configs({}, old_config) if old_config else []

    config_changes.sort(key=lambda c: c.effect_size, reverse=True)

    expert_insights_report = None
    if expert_doc_paths:
        logger.info("Step 5a/6: Parsing expert documents...")

        llm = None
        try:
            from app.llm.base import LLMFactory
            from app.config import settings
            llm = LLMFactory.create(settings.llm_provider)
        except Exception as exc:
            logger.warning(f"Cannot create LLM adapter for expert parsing: {exc}")

        expert_insights_list = []
        for doc_path in expert_doc_paths:
            try:
                insights = unify_parse(doc_path, llm)
                expert_insights_list.append(insights)
            except Exception as exc:
                logger.warning(f"Failed to parse expert doc '{doc_path}': {exc}")
        if expert_insights_list:
            merged = merge_insights(*expert_insights_list)
            expert_insights_report = insights_report_markdown(merged)
            logger.info(
                f"Expert insights: {len(merged.annotations)} annotations from "
                f"{len(merged.authors)} author(s)"
            )

    logger.info("Step 6/6: Generating calibration report...")
    report = generate_calibration_report(
        competition=competition,
        competition_type=competition_type,
        effect_sizes=effect_sizes,
        cross_validations=cross_validations,
        config_changes=config_changes,
        config_diff=config_diff,
        n_winners=len(winners_features),
        n_losers=len(losers_features),
        n_external=len(external_features),
        expert_insights_report=expert_insights_report,
    )

    if output_report_path:
        Path(output_report_path).write_text(report, encoding="utf-8")
        logger.info(f"Report saved to {output_report_path}")

    try:
        from app.utils.sync import report_calibration
        import asyncio
        asyncio.ensure_future(report_calibration({
            "competition": competition,
            "competition_type": competition_type,
            "n_winners": len(winners_features),
            "n_losers": len(losers_features),
            "n_external": len(external_features),
            "effect_sizes": [es.__dict__ for es in effect_sizes] if effect_sizes else [],
            "config_changes": [c.__dict__ for c in config_changes] if config_changes else [],
        }))
    except Exception:
        pass

    return report
