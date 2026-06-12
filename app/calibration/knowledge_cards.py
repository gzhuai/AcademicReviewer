"""
知识卡自动分层 —— 将 ExpertInsights 按三层分类，供 Orchestrator 注入 Agent prompt。

Layer 1 (核心必填): what_excellence_looks_like + fatal_defects + scoring_anchors
Layer 2 (标杆案例): 好/差段落对照文本
Layer 3 (自由笔记): 教学策略、随手记、未分类经验
"""

from __future__ import annotations


def build_knowledge_cards(insights) -> dict:
    """将 ExpertInsights 自动分层为三层知识卡。

    Args:
        insights: ExpertInsights 实例（来自 expert_annotator.parse_expert_document()
                  或 expert_freeform_parser.unify_parse()）

    Returns:
        dict with keys:
            layer_1_core: {what_excellence_looks_like, fatal_defects, scoring_anchors}
            layer_2_benchmarks: list[Annotation]
            layer_3_notes: list[Annotation]
    """
    if insights is None:
        return _empty_cards()

    annotations = getattr(insights, "annotations", [])
    if not annotations:
        return _empty_cards()

    cards = {
        "layer_1_core": {
            "what_excellence_looks_like": [],
            "fatal_defects": [],
            "scoring_anchors": [],
        },
        "layer_2_benchmarks": [],
        "layer_3_notes": [],
    }

    for a in annotations:
        anno_type = getattr(a, "annotation_type", "")
        if anno_type in ("pattern", "pitfall", "signal"):
            cards["layer_1_core"]["what_excellence_looks_like"].append(a)
        elif anno_type == "fatal_defect":
            cards["layer_1_core"]["fatal_defects"].append(a)
        elif anno_type == "scoring_anchor":
            cards["layer_1_core"]["scoring_anchors"].append(a)
        elif anno_type == "benchmark":
            cards["layer_2_benchmarks"].append(a)
        else:
            cards["layer_3_notes"].append(a)

    return cards


def render_knowledge_cards_for_prompt(cards: dict) -> str:
    """将知识卡渲染为可注入 Agent prompt 的文本块。

    只渲染 Layer 1 (核心) 和 Layer 2 (标杆案例) 到 prompt。
    Layer 3 (自由笔记) 不注入 —— 它仅供老师参考。
    """
    parts = []

    l1 = cards.get("layer_1_core", {})
    if l1:
        parts.append("【教师知识卡 — 核心标准】")

        # 1. What excellence looks like
        weal = l1.get("what_excellence_looks_like", [])
        if weal:
            parts.append("## 优秀作品的标准")
            for a in weal:
                parts.append(_format_annotation(a))

        # 2. Fatal defects (hard red lines)
        fd = l1.get("fatal_defects", [])
        if fd:
            parts.append("## 致命缺陷 / 硬红线")
            parts.append("以下项一旦命中，总分自动受限：")
            for a in fd:
                parts.append(_format_annotation(a))

        # 3. Scoring anchors
        sa = l1.get("scoring_anchors", [])
        if sa:
            parts.append("## 评分锚点（各分数段典型特征）")
            for a in sa:
                parts.append(_format_annotation(a))

    # Layer 2: Benchmarks (do/do-not examples)
    l2 = cards.get("layer_2_benchmarks", [])
    if l2:
        parts.append("【教师知识卡 — 标杆案例】")
        parts.append("注意：这些是老师认可的正面/反面案例，评审时请将学生的写作与这些标杆对比。")
        for a in l2:
            parts.append(_format_annotation(a))

    return "\n\n".join(parts)


def _format_annotation(a) -> str:
    """将单个 Annotation 格式化为文本行。"""
    title = getattr(a, "title", "")
    description = getattr(a, "description", "")
    feature = getattr(a, "feature_name", "")
    anno_type = getattr(a, "annotation_type", "")

    prefix = {
        "fatal_defect": "🔴 [致命缺陷]",
        "scoring_anchor": "📊 [评分锚点]",
        "benchmark": "📋 [标杆]",
        "pattern": "📌 [获奖模式]",
        "pitfall": "⚠️ [常见问题]",
        "signal": "📡 [高分信号]",
    }.get(anno_type, f"[{anno_type}]")

    lines = [f"{prefix} {title}"]
    if feature:
        lines.append(f"  特征: {feature}")
    if description:
        lines.append(f"  {description}")
    return "\n".join(lines)


def _empty_cards() -> dict:
    return {
        "layer_1_core": {
            "what_excellence_looks_like": [],
            "fatal_defects": [],
            "scoring_anchors": [],
        },
        "layer_2_benchmarks": [],
        "layer_3_notes": [],
    }
