"""
教师经验标注引擎

解析教师撰写的结构化经验文档，将多年教学评审的隐性知识
转化为可与统​​计校准管道融合的结构化洞察。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


ANNOTATION_TYPES = (
    "pattern", "pitfall", "rubric", "signal", "strategy",
    "fatal_defect",    # 致命缺陷 / 硬红线 — 总分自动受限
    "benchmark",        # 好/差对照案例 — AI 判断质量的参照物
    "scoring_anchor",   # 分数锚点 — 各分数段的典型特征描述
)

FEATURE_KEYWORDS: dict[str, list[str]] = {
    "citation_density": ["引用", "citation", "文献密度", "参考文献", "bibliography", "reference"],
    "passive_voice_ratio": ["被动", "passive", "语态", "voice"],
    "vocabulary_diversity": ["词汇", "vocabulary", "用词", "ttr", "多样性"],
    "logical_marker_density": ["逻辑", "logical", "连接词", "marker", "过渡词"],
    "transition_frequency": ["过渡", "transition", "衔接", "起承转合"],
    "avg_sentence_length": ["句子长度", "sentence length", "长句", "短句"],
    "sentence_length_std": ["句子波动", "sentence variation", "句长变化"],
    "section_coverage": ["章节", "section", "结构完整", "coverage", "结构"],
    "has_p_value": ["p值", "p-value", "显著性", "significant", "统计检验"],
    "has_effect_size": ["效应量", "effect size", "effect"],
    "has_control_group": ["对照组", "control group", "control", "对照"],
    "has_sample_size": ["样本量", "sample size", "sample", "样本"],
    "evidence_diversity_score": ["证据", "evidence", "来源", "source type", "数据来源"],
    "gap_statement_present": ["研究空白", "gap", "研究差距", "空白", "gap statement"],
    "limitations_section_present": ["局限性", "limitation", "不足", "局限"],
    "future_work_mentioned": ["未来研究", "future work", "后续", "展望"],
}


@dataclass
class ExpertAnnotation:
    annotation_type: Literal["pattern", "pitfall", "rubric", "signal", "strategy"]
    title: str
    description: str
    author: str = ""
    mapped_features: list[str] = field(default_factory=list)
    confidence: float = 1.0
    competition: str = ""

    @property
    def is_qualitative(self) -> bool:
        return not self.mapped_features


@dataclass
class ExpertInsights:
    competition: str
    authors: list[str] = field(default_factory=list)
    annotations: list[ExpertAnnotation] = field(default_factory=list)

    @property
    def feature_mapped(self) -> list[ExpertAnnotation]:
        return [a for a in self.annotations if a.mapped_features]

    @property
    def qualitative_only(self) -> list[ExpertAnnotation]:
        return [a for a in self.annotations if not a.mapped_features]

    @property
    def patterns(self) -> list[ExpertAnnotation]:
        return [a for a in self.annotations if a.annotation_type == "pattern"]

    @property
    def pitfalls(self) -> list[ExpertAnnotation]:
        return [a for a in self.annotations if a.annotation_type == "pitfall"]

    @property
    def signals(self) -> list[ExpertAnnotation]:
        return [a for a in self.annotations if a.annotation_type == "signal"]

    @property
    def strategies(self) -> list[ExpertAnnotation]:
        return [a for a in self.annotations if a.annotation_type == "strategy"]

    def get_by_feature(self, feature_name: str) -> list[ExpertAnnotation]:
        return [a for a in self.annotations if feature_name in a.mapped_features]


_SECTION_RE = re.compile(
    r"^###\s*\[(\w+)\]\s*(\S*)",
    re.MULTILINE,
)
_FIELD_RE = re.compile(r"^\*\*(.+?)\*\*:\s*(.+)", re.MULTILINE)
_META_RE = re.compile(r"^##\s*(.+?):\s*(.+)", re.MULTILINE)


def parse_expert_document(file_path: str) -> ExpertInsights:
    text = Path(file_path).read_text(encoding="utf-8", errors="replace")

    competition = ""
    author = ""
    for m in _META_RE.finditer(text):
        key = m.group(1).strip()
        value = m.group(2).strip()
        if key in ("竞赛", "竞赛名称", "Competition"):
            competition = value
        elif key in ("作者", "教师", "Author", "Teacher"):
            author = value

    annotations: list[ExpertAnnotation] = []
    sections = list(_SECTION_RE.finditer(text))
    for i, sec_match in enumerate(sections):
        anno_type = sec_match.group(1)
        explicit_feature = sec_match.group(2).strip()

        if anno_type not in ANNOTATION_TYPES:
            continue

        start = sec_match.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
        body = text[start:end]

        title = ""
        description = ""
        linked_features_str = ""

        for fm in _FIELD_RE.finditer(body):
            fname = fm.group(1).strip()
            fval = fm.group(2).strip()
            if fname in ("标题", "Title"):
                title = fval
            elif fname in ("描述", "说明", "Description"):
                description = fval
            elif fname in ("关联特征", "Related Features", "特征"):
                linked_features_str = fval

        if not title and not description:
            cleaned = body.strip()
            lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
            if lines:
                title = lines[0] if lines[0] else ""
                description = "\n".join(lines[1:]) if len(lines) > 1 else ""

        mapped = _resolve_features(
            explicit_feature=explicit_feature,
            linked_features_str=linked_features_str,
            title=title,
            description=description,
        )

        annotations.append(ExpertAnnotation(
            annotation_type=anno_type,  # type: ignore[arg-type]
            title=title,
            description=description,
            author=author,
            mapped_features=mapped,
            competition=competition,
        ))

    logger.info(
        f"Parsed expert doc '{file_path}': "
        f"author={author}, competition={competition}, annotations={len(annotations)}"
    )

    return ExpertInsights(
        competition=competition,
        authors=[author] if author else [],
        annotations=annotations,
    )


def _resolve_features(
    explicit_feature: str,
    linked_features_str: str,
    title: str,
    description: str,
) -> list[str]:
    mapped: list[str] = []

    if explicit_feature and explicit_feature in FEATURE_KEYWORDS:
        mapped.append(explicit_feature)

    if linked_features_str:
        for part in re.split(r"[,，;；\s]+", linked_features_str):
            part = part.strip()
            if part in FEATURE_KEYWORDS:
                if part not in mapped:
                    mapped.append(part)

    if not mapped:
        search_text = f"{title} {description}".lower()
        for feat, keywords in FEATURE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in search_text:
                    if feat not in mapped:
                        mapped.append(feat)
                    break

    return mapped[:5]


def merge_insights(*insights: ExpertInsights) -> ExpertInsights:
    all_authors: list[str] = []
    all_annotations: list[ExpertAnnotation] = []
    competition = ""

    for ins in insights:
        if ins.competition:
            competition = ins.competition
        for a in ins.authors:
            if a not in all_authors:
                all_authors.append(a)
        all_annotations.extend(ins.annotations)

    return ExpertInsights(
        competition=competition,
        authors=all_authors,
        annotations=all_annotations,
    )


def insights_report_markdown(insights: ExpertInsights) -> str:
    if not insights.annotations:
        return ""

    lines: list[str] = []
    lines.append("## 教师经验洞察")
    lines.append("")

    if insights.authors:
        authors_str = "、".join(insights.authors)
        lines.append(f"> 贡献者: {authors_str}")
    if insights.competition:
        lines.append(f"> 竞赛: {insights.competition}")
    lines.append("")

    patterns = insights.patterns
    if patterns:
        lines.append("### 观察到的获奖模式")
        lines.append("")
        for i, p in enumerate(patterns, 1):
            lines.append(f"**{i}. {p.title}**")
            if p.mapped_features:
                feat_labels = [FEATURE_KEYWORDS.get(f, [f])[0] for f in p.mapped_features]
                lines.append(f"*关联特征: {', '.join(feat_labels)}*")
            lines.append("")
            for para in p.description.split("\n"):
                if para.strip():
                    lines.append(f"  {para.strip()}")
            lines.append("")
            if p.author:
                lines.append(f"  *— {p.author}*")
            lines.append("")

    pitfalls = insights.pitfalls
    if pitfalls:
        lines.append("### 常见陷阱")
        lines.append("")
        for i, p in enumerate(pitfalls, 1):
            lines.append(f"**{i}. {p.title}**")
            if p.mapped_features:
                feat_labels = [FEATURE_KEYWORDS.get(f, [f])[0] for f in p.mapped_features]
                lines.append(f"*关联特征: {', '.join(feat_labels)}*")
            lines.append("")
            for para in p.description.split("\n"):
                if para.strip():
                    lines.append(f"  {para.strip()}")
            lines.append("")
            if p.author:
                lines.append(f"  *— {p.author}*")
            lines.append("")

    signals = insights.signals
    if signals:
        lines.append("### 获奖信号")
        lines.append("")
        for i, s in enumerate(signals, 1):
            lines.append(f"**{i}. {s.title}**")
            lines.append("")
            for para in s.description.split("\n"):
                if para.strip():
                    lines.append(f"  {para.strip()}")
            lines.append("")
            if s.author:
                lines.append(f"  *— {s.author}*")
            lines.append("")

    strategies = insights.strategies
    if strategies:
        lines.append("### 教学策略建议")
        lines.append("")
        for i, s in enumerate(strategies, 1):
            lines.append(f"**{i}. {s.title}**")
            lines.append("")
            for para in s.description.split("\n"):
                if para.strip():
                    lines.append(f"  {para.strip()}")
            lines.append("")
            if s.author:
                lines.append(f"  *— {s.author}*")
            lines.append("")

    lines.append("---")
    lines.append("*注: 教师经验洞察基于人工标注，请与统计数据交叉验证。*")
    lines.append("")

    return "\n".join(lines)


def unify_parse(file_path: str, llm=None) -> ExpertInsights:
    text = Path(file_path).read_text(encoding="utf-8", errors="replace")

    if _SECTION_RE.search(text):
        return parse_expert_document(file_path)

    if llm is None:
        raise ValueError(
            f"文档 '{file_path}' 为自由格式 (Mode 1/2)，需要 LLM 适配器。"
            f"请提供 LLM 实例，或使用 Mode 3 结构化格式。"
        )

    from app.calibration.expert_freeform_parser import parse_freeform_expert_doc
    return parse_freeform_expert_doc(file_path, llm)
