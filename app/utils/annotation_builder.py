"""
原文标注生成器 — 将 5-Agent 反馈映射回原始文档，生成带标注的 Markdown

输出格式如 Word 修订模式：原文段落 + 各 Agent 的批注和改写建议。
v0.4.0: 支持置信度标签（FULL/REVIEW/ESCALATE）分级显示。
"""

from __future__ import annotations
import re

from app.utils.confidence_engine import get_substitutability_emoji
from app.utils.text_utils import split_paragraphs, parse_location


def build_annotated_markdown(
    original_text: str,
    structure: dict | None = None,
    argument: dict | None = None,
    language: dict | None = None,
    integrity: dict | None = None,
    rubric: dict | None = None,
) -> str:
    """生成带标注的 Markdown 文档。"""
    paragraphs = split_paragraphs(original_text)
    if not paragraphs:
        return original_text or "*（空文档）*"

    lines = []
    lines.append("# 审稿标注报告\n")
    lines.append("> 标注格式：每个段落后方显示该段落涉及的审稿意见。")
    lines.append("> A2 = 结构逻辑  |  A3 = 论点证据  |  A4 = 语言风格  |  A5 = 学术诚信")
    lines.append("> 置信度：无标记 = AI可替代(FULL)  |  ⚡ = 需确认(REVIEW)  |  🔴 = 必须人工(ESCALATE)\n")

    # Collect language rewrite suggestions by paragraph index
    rewrites_by_para = {}
    if language:
        for rw in language.get("rewrites", []):
            loc = parse_location(rw.get("location", ""))
            rewrites_by_para.setdefault(loc, []).append(rw)

    # Suggest paragraphs with weak spots
    structure_issues_by_para = {}
    if structure:
        for si in structure.get("section_issues", []):
            section = si.get("section", "")
            for i, para in enumerate(paragraphs):
                if section.lower() in para.lower()[:80]:
                    structure_issues_by_para.setdefault(i, []).append(si)

    logic_gaps = {}
    if structure:
        for li in structure.get("logic_issues", []):
            loc = li.get("location", "")
            # try to find paragraph index containing transition point
            for i, para in enumerate(paragraphs):
                if any(w in para.lower()[:80] for w in loc.lower().split("→")):
                    logic_gaps.setdefault(i, []).append(li)
                    break

    # Paragraph-by-paragraph rendering
    for i, para in enumerate(paragraphs):
        lines.append(f"\n### 段落 {i+1}\n")
        lines.append(para)
        lines.append("")

        annotations = []

        # A4 rewrites for this paragraph
        rw_list = rewrites_by_para.get(i, [])
        for rw in rw_list:
            orig = rw.get("original", "")
            corr = rw.get("corrected", "")
            issue = rw.get("issue", "")
            sub = rw.get("substitutability", "")
            emoji = get_substitutability_emoji(sub)
            if orig and corr and orig != corr:
                annotations.append(f"> {emoji}**[A4-{issue}]** `{orig}` → `{corr}`")
            elif orig and not corr:
                annotations.append(f"> {emoji}**[A4-{issue}]** 此项无需修改")

        # A2 structure issues for this paragraph
        si_list = structure_issues_by_para.get(i, [])
        for si in si_list:
            issue_text = si.get("issue", "")
            hint = si.get("hint", "")
            sev = si.get("severity", "?")
            sub = si.get("substitutability", "")
            emoji = get_substitutability_emoji(sub)
            label = {"high": "!!", "medium": "!", "low": "i"}.get(sev, "?")
            annotations.append(f"> {emoji}**[A2{label}—{sev}]** {issue_text}")
            if hint:
                annotations.append(f">   *{hint}*")

        # A3 fallacies in this paragraph
        if argument:
            for fl in argument.get("logical_fallacies", []):
                fl_loc = fl.get("location", "")
                if _match_location(fl_loc, para, i):
                    sub = fl.get("substitutability", "")
                    emoji = get_substitutability_emoji(sub)
                    annotations.append(
                        f"> {emoji}**[A3!!—逻辑谬误]** {fl.get('fallacy_type')}: {fl.get('description', '')}"
                    )
                    correct = fl.get("correct_form", "")
                    if correct:
                        annotations.append(f">   正确推理: {correct}")

        # A2 duplication
        if structure:
            for dr in structure.get("duplication_report", []):
                para_names = dr.get("paragraphs", [])
                if f"第{i+1}段" in para_names or f"段落{i+1}" in str(para_names):
                    annotations.append(f"> **[A2—重复]** {dr.get('repeated_content', '')}")
                    annotations.append(f">   *修复: {dr.get('fix', '')}*")

        # A5 citation issues
        if integrity:
            cr = integrity.get("citation_report", {})
            cr_sub = cr.get("substitutability", "")
            cr_emoji = get_substitutability_emoji(cr_sub)
            for sc in cr.get("suspicious_citations", []):
                if _match_location(sc, para, i):
                    annotations.append(f"> {cr_emoji}**[A5!—引用]** {sc}")

        if annotations:
            lines.extend(annotations)

    # --- Overview section ---
    lines.append("\n---\n")
    lines.append("## 总结\n")

    if structure:
        lines.append(f"\n### 结构 (A2) — {structure.get('structure_score', '?')}/10\n")
        # Support both old field name and new
        tc = structure.get("main_argument_coaching") or structure.get("thesis_coaching", {})
        if tc.get("current_statement") or tc.get("current_thesis"):
            lines.append(f"**当前论点:** {tc.get('current_statement') or tc.get('current_thesis', '')}")
        if tc.get("stronger_version"):
            lines.append(f"**更强版本:** {tc['stronger_version']}")
        if tc.get("vulnerability"):
            lines.append(f"**脆弱点:** {tc['vulnerability']}")
        for p in structure.get("positive_points", []):
            lines.append(f"- ✅ {p}")
        for ki in structure.get("key_issues", []):
            lines.append(f"- ⚠️ {ki}")

    if argument:
        lines.append(f"\n### 论证 (A3) — {argument.get('overall_score', '?')}/10\n")
        # Support both old field name and new
        vp = argument.get("validation_point") or argument.get("counterargument_analysis", {})
        if vp.get("coach_guidance"):
            lines.append(f"**竞赛专项审查:** {vp['coach_guidance']}")
        elif vp.get("strongest_objection_not_addressed"):
            lines.append(f"**未回应的最强反方:** {vp['strongest_objection_not_addressed']}")
        if vp.get("rebuttal_guidance") or vp.get("word_count_suggestion"):
            lines.append(f"**指导:** {vp.get('rebuttal_guidance') or vp.get('word_count_suggestion', '')}")
        for p in argument.get("positive_points", []):
            lines.append(f"- ✅ {p}")
        for ki in argument.get("key_issues", []):
            lines.append(f"- ⚠️ {ki}")

    if integrity:
        lines.append(f"\n### 学术诚信 (A5) — {integrity.get('integrity_score', '?')}/10\n")
        cr = integrity.get("citation_report", {})
        or_report = integrity.get("originality_report", {})
        cr_sub = cr.get("substitutability", "")
        or_sub = or_report.get("substitutability", "")
        cr_emoji = get_substitutability_emoji(cr_sub)
        or_emoji = get_substitutability_emoji(or_sub)
        lines.append(f"- {cr_emoji} 引用检查 (A5a): {cr.get('match_rate', '?')*100:.0f}% 匹配 ({cr.get('matched', 0)}/{cr.get('total_cites', 0)})")
        lines.append(f"- {or_emoji} 原创性检查 (A5b): {or_report.get('originality_score', '?')}/10")
        for pp in integrity.get("positive_points", []):
            lines.append(f"- ✅ {pp}")
        for ki in integrity.get("key_issues", []):
            lines.append(f"- ⚠️ {ki}")

    if rubric:
        lines.append("\n### 评分维度 (A1)\n")
        for dim in rubric.get("dimensions", []):
            lines.append(f"- **{dim['name']}** (权重 {int(dim['weight']*100)}%): {dim.get('level_descriptions', {}).get('excellent', '')[:80]}...")

    return "\n".join(lines)


def _match_location(loc_text: str, paragraph: str, para_index: int) -> bool:
    """模糊匹配位置描述与段落。"""
    idx = parse_location(loc_text)
    if idx >= 0 and idx == para_index:
        return True
    # fallback: keyword match
    keywords = loc_text.replace("第", "").replace("段", "").strip()
    if keywords and len(keywords) > 3 and keywords.lower() in paragraph.lower():
        return True
    return False
