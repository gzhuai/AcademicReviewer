"""
置信度规则引擎 —— 在 Agent 输出后、annotation_builder 组装前运行。

根据 HUMAN_AGENT_COLLABORATION.md 的方案 B，置信度标签不由 LLM 自评，
而是由规则引擎根据 Agent 类型和输出条目类型确定：

- 结构检测（格式、拼写、章节完整性）→ FULL
- 语义判断（论证强度、逻辑连贯性）→ REVIEW
- 领域深度判断（原创性、哲学立场、模型选型）→ ESCALATE

用法:
    from app.utils.confidence_engine import apply_confidence_labels

    structure = apply_confidence_labels("StructureLogic", structure_result)
    argument = apply_confidence_labels("ArgumentEvidence", argument_result)
    language = apply_confidence_labels("LanguageStyle", language_result)
    integrity = apply_confidence_labels("AcademicIntegrity", integrity_result)
"""

from __future__ import annotations

# ── 按 Agent + 条目类型的默认 substitutability 映射 ──
# 键: (agent_name, field_name) → 默认 substitutability
_AGENT_FIELD_DEFAULTS: dict[tuple[str, str], str] = {
    # A2 StructureLogic: section missing → mechanical check → FULL
    ("StructureLogic", "section_issues"): "REVIEW",
    ("StructureLogic", "logic_issues"): "REVIEW",

    # A3 ArgumentEvidence
    ("ArgumentEvidence", "claims"): "REVIEW",
    ("ArgumentEvidence", "logical_fallacies"): "REVIEW",

    # A4 LanguageStyle: rewrites are surface fixes → FULL; suggestions are subjective → REVIEW
    ("LanguageStyle", "rewrites"): "FULL",
    ("LanguageStyle", "suggestions"): "REVIEW",

    # A5 AcademicIntegrity: citation matching is rule-based → FULL; originality → ESCALATE
    ("AcademicIntegrity", "citation_report"): "FULL",
    ("AcademicIntegrity", "originality_report"): "ESCALATE",
}

# ── 按条目内容特征的细化规则 ──
# 在默认的基础上，根据条目具体内容微调

# A4 rewrites 的 issue 类型 → substitutability 微调
_A4_REWRITE_ISSUE_MAP: dict[str, str] = {
    "spelling": "FULL",
    "grammar": "FULL",
    "punctuation": "FULL",
    "chinglish": "FULL",
}

# A4 suggestions 的 type → substitutability 微调
_A4_SUGGESTION_TYPE_MAP: dict[str, str] = {
    "passive_voice": "REVIEW",
    "sentence_length": "REVIEW",
    "word_choice": "REVIEW",
    "transition": "REVIEW",
    "clarity": "REVIEW",
    "redundancy": "FULL",  # 重复检测是机械的
}

# A3 logical_fallacies 的 fallacy_type → substitutability
_A3_FALLACY_TYPE_MAP: dict[str, str] = {
    # 结构性谬误（可通过文本模式检测）→ FULL
    "begging_question": "FULL",
    "false_dichotomy": "FULL",
    # 语义性谬误（需理解论证内容）→ REVIEW
    "straw_man": "REVIEW",
    "weak_analogy": "REVIEW",
    "false_cause": "REVIEW",
    "hasty_generalization": "REVIEW",
    "slippery_slope": "REVIEW",
    "correlation_not_causation": "REVIEW",
    "confounding_variable": "REVIEW",
    "survivorship_bias": "REVIEW",
    "hindsight_bias": "REVIEW",
}

# A2 section_issues severity → substitutability
# high severity missing required sections → FULL (mechanical), rest → REVIEW
_A2_SECTION_SEVERITY_MAP: dict[str, str] = {
    "high": "FULL",    # 缺少必需章节 → 机械检查
    "medium": "REVIEW",
    "low": "REVIEW",
}


def apply_confidence_labels(agent_name: str, result: dict | None) -> dict | None:
    """对 Agent 输出应用规则引擎的置信度标签 + 数据清洗。

    在 LLM 输出的基础上，根据规则微调每条目的 substitutability。
    同时执行数据清洗：剔除 original==corrected 的假阳性 rewrite 条目。
    保留 LLM 可能已经填写的 confidence_rationale，如果 LLM 没填则不补充。
    """
    if not result or not isinstance(result, dict):
        return result

    result = dict(result)  # shallow copy to avoid mutating caller's dict

    if agent_name == "StructureLogic":
        _apply_to_list(result, "section_issues", agent_name,
                       severity_map=_A2_SECTION_SEVERITY_MAP, severity_key="severity")
        _apply_to_list(result, "logic_issues", agent_name)

    elif agent_name == "ArgumentEvidence":
        _apply_to_list(result, "claims", agent_name)
        _apply_to_list(result, "logical_fallacies", agent_name,
                       type_map=_A3_FALLACY_TYPE_MAP, type_key="fallacy_type")

    elif agent_name == "LanguageStyle":
        # ── 数据清洗：剔除 original==corrected 的假阳性 rewrite 条目 ──
        _sanitize_rewrites(result)
        _apply_to_list(result, "rewrites", agent_name,
                       type_map=_A4_REWRITE_ISSUE_MAP, type_key="issue")
        _apply_to_list(result, "suggestions", agent_name,
                       type_map=_A4_SUGGESTION_TYPE_MAP, type_key="type")

    elif agent_name == "AcademicIntegrity":
        _apply_to_report_field(result, "citation_report", agent_name)
        _apply_to_report_field(result, "originality_report", agent_name)

    return result


def _sanitize_rewrites(result: dict) -> None:
    """剔除 A4 rewrites 列表中 original == corrected 的假阳性条目。

    LLM（尤其是 DeepSeek）常见的幻觉行为：逐句检查每一句话，
    即使没有语法错误也生成一条 rewrite 条目，导致 80+ 条完全相同的条目。
    此函数在数据入库前进行后处理清洗。
    """
    rewrites = result.get("rewrites")
    if not isinstance(rewrites, list):
        return

    removed_count = 0
    kept = []
    for rw in rewrites:
        if not isinstance(rw, dict):
            removed_count += 1
            continue
        orig = (rw.get("original") or "").strip()
        corr = (rw.get("corrected") or "").strip()
        if not orig or not corr:
            removed_count += 1
            continue
        if orig == corr:
            removed_count += 1
            continue
        kept.append(rw)

    if removed_count > 0:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"[LanguageStyle] Sanitized rewrites: removed {removed_count} "
            f"false-positive entries (original==corrected or empty), kept {len(kept)}"
        )
        result["rewrites"] = kept
        # 同步更新 summary 中的 rewrite_count（如果存在）
        summary = result.get("summary")
        if isinstance(summary, dict):
            summary["rewrite_count"] = len(kept)
            # 如果之前是包含水分的数量，记录原始值
            summary["rewrite_count_before_sanitize"] = len(rewrites)


def _apply_to_list(result: dict, field: str, agent_name: str,
                   type_map: dict[str, str] | None = None,
                   type_key: str = "",
                   severity_map: dict[str, str] | None = None,
                   severity_key: str = "") -> None:
    """对 result[field] 列表中的每个条目应用默认 + 细化规则。"""
    items = result.get(field)
    if not isinstance(items, list):
        return

    default_label = _AGENT_FIELD_DEFAULTS.get((agent_name, field), "REVIEW")

    for item in items:
        if not isinstance(item, dict):
            continue
        # 确定最终标签：细化规则 > 默认规则
        label = default_label
        if type_map and type_key:
            item_type = item.get(type_key, "")
            if item_type in type_map:
                label = type_map[item_type]
        if severity_map and severity_key:
            sev = item.get(severity_key, "")
            if sev in severity_map:
                label = severity_map[sev]

        item["substitutability"] = label


def _apply_to_report_field(result: dict, field: str, agent_name: str) -> None:
    """对 report 级别的字段（如 citation_report/originality_report）应用标签。"""
    report = result.get(field)
    if not isinstance(report, dict):
        return

    default_label = _AGENT_FIELD_DEFAULTS.get((agent_name, field), "REVIEW")
    report["substitutability"] = default_label


def get_substitutability_label(substitutability: str) -> str:
    """获取 substitutability 标签的显示文本。"""
    return {
        "FULL": "FULL",
        "REVIEW": "REVIEW",
        "ESCALATE": "ESCALATE",
    }.get(substitutability, "REVIEW")


def get_substitutability_emoji(substitutability: str) -> str:
    """获取 substitutability 对应的 emoji 标记。"""
    return {
        "FULL": "",
        "REVIEW": "⚡",
        "ESCALATE": "🔴",
    }.get(substitutability, "")


def get_substitutability_description(substitutability: str) -> str:
    """获取 substitutability 的中文说明。"""
    return {
        "FULL": "AI可完全替代老师，无需审核",
        "REVIEW": "需老师确认",
        "ESCALATE": "必须老师审核",
    }.get(substitutability, "")
