"""
自由格式教师经验解析器

支持两种非结构化输入模式:
  Mode 2 (半结构化): 文档包含 ## 已知章节标题 → 章节路由 + LLM 辅助拆分条目
  Mode 1 (纯自由文本): 无任何结构标记 → 全文 LLM 语义解析

Mode 3 (全结构化) 由 expert_annotator.parse_expert_document() 处理。

LLM 仅负责将自然语言文本拆分为结构化条目，
特征映射始终走本地 FEATURE_KEYWORDS 关键词匹配（确定性，零幻觉风险）。
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from app.calibration.expert_annotator import (
    ANNOTATION_TYPES,
    ExpertAnnotation,
    ExpertInsights,
    FEATURE_KEYWORDS,
    _resolve_features,
    _read_expert_text,
)

logger = logging.getLogger(__name__)

SECTION_TITLE_PATTERNS: dict[str, list[str]] = {
    "pattern": [
        "获奖经验", "获奖规律", "获奖模式", "成功案例", "成功案例总结",
        "晋级规律", "获奖论文的共同特征", "高频特征", "获奖特征", "获奖共同点",
        "好的做法", "优秀案例", "亮点总结",
    ],
    "pitfall": [
        "常见问题", "常见错误", "易踩的坑", "学生通病", "常见扣分点",
        "失败案例总结", "典型问题", "常见误区", "不足之处", "需改进的问题",
        "常见失误", "扣分项",
    ],
    "signal": [
        "高分信号", "晋级信号", "决赛特征", "评审偏好", "加分项",
        "获奖信号", "评委看重什么", "评委关注点", "高分特征", "评审标准倾向",
    ],
    "strategy": [
        "教学方法", "辅导策略", "训练方法", "写作建议", "提升方法",
        "备考策略", "教学心得", "辅导心得", "练习方法", "训练建议",
        "指导方法",
    ],
    "fatal_defect": [
        "致命缺陷", "一票否决", "红线", "硬性标准", "绝不接受",
        "最低要求", "必须避免", "绝对禁止", "零容忍",
    ],
    "benchmark": [
        "标杆案例", "范例", "好文案例", "差文对比", "范文片段",
        "标杆", "示例对比", "好 vs 差", "正确做法", "错误做法",
    ],
    "scoring_anchor": [
        "评分锚点", "打分参考", "各分数段标准", "评分标准细化",
        "分数对照", "评级描述", "各档位标准",
    ],
    "rubric": [
        "评分标准解读", "评分细则", "评审规则理解", "评分表解读",
        "评分标准", "评审体系",
    ],
}

_META_RE = re.compile(r"^##\s*(.+?):\s*(.+)", re.MULTILINE)
_FULL_STRUCTURED_RE = re.compile(r"^###\s*\[", re.MULTILINE)

_SECTION_HEADER_RE = re.compile(
    r"^##\s+(.+?)$",
    re.MULTILINE,
)


def detect_mode(text: str) -> int:
    if _FULL_STRUCTURED_RE.search(text):
        return 3
    for m in _SECTION_HEADER_RE.finditer(text):
        title = m.group(1).strip()
        for titles in SECTION_TITLE_PATTERNS.values():
            if title in titles:
                return 2
    return 1


def _extract_meta(text: str) -> tuple[str, str]:
    competition = ""
    author = ""
    for m in _META_RE.finditer(text):
        key = m.group(1).strip()
        value = m.group(2).strip()
        if key in ("竞赛", "竞赛名称", "Competition"):
            competition = value
        elif key in ("作者", "教师", "Author", "Teacher"):
            author = value
    return competition, author


def _split_sections_mode2(text: str) -> list[tuple[str, str]]:
    matches = list(_SECTION_HEADER_RE.finditer(text))
    sections: list[tuple[str, str]] = []

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        anno_type = ""
        for a_type, titles in SECTION_TITLE_PATTERNS.items():
            if title in titles:
                anno_type = a_type
                break
        if not anno_type:
            continue

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((anno_type, body))

    return sections


_EXTRACTION_SYSTEM_PROMPT = """你是一个教育领域的知识提取专家。你的任务是将教师的教学经验文本中的每个独立洞察，提取为结构化的 JSON 条目。

规则:
1. 每个条目必须包含 title (15字以内的精炼标题) 和 description (保留原文关键信息，去除口语化表达，但不要润色或添加内容)
2. 一个条目对应一个独立的洞察或经验点。不要将多个洞察合并
3. 不要添加原文中没有的内容或数据
4. 如果文本中没有明确的经验洞察内容，返回空列表
5. 使用原文的语言（中文）

annotation_type 的取值由调用方指定，直接继承即可，不要修改。

输出格式:
{"items": [{"title": "...", "description": "...", "annotation_type": "..."}]}

示例输入 (annotation_type: "pitfall"):
中国学生普遍过度使用被动语态，通常超过35%，这是被扣分的主要原因之一。ISEF评审偏好主动语态，尤其是在方法论和结论部分。建议将被动语态控制在20%以下。

示例输出:
{"items": [{"title": "过度使用被动语态导致扣分", "description": "中国学生被动语态占比通常超过35%，这是常见扣分原因。ISEF评审偏好主动语态，建议控制在20%以下，尤其在方法论和结论部分。", "annotation_type": "pitfall"}]}"""

_EXTRACTION_SYSTEM_PROMPT_MODE1 = """你是一个教育领域的知识提取专家。你的任务是将教师的教学经验文本中的每个独立洞察，提取为结构化的 JSON 条目。

规则:
1. 每个条目必须包含 title (15字以内的精炼标题)、description (保留原文关键信息，去除口语化表达，但不要润色或添加内容) 和 annotation_type
2. 一个条目对应一个独立的洞察或经验点。不要将多个洞察合并
3. 不要添加原文中没有的内容或数据
4. 使用原文的语言（中文）

annotation_type 必须是以下五种之一:
- pattern: 教师观察到的获奖模式或成功规律
- pitfall: 学生常见的错误和扣分陷阱
- signal: 评审偏好的高分信号或获奖标志
- strategy: 教师推荐的教学策略或训练方法
- rubric: 对评分标准的理解和解读

判断 annotation_type 的标准:
- 如果描述的是"获奖学生通常..."、"我发现入围的学生..."这类观察，归类为 pattern
- 如果描述的是"学生经常..."、"最大的问题是..."、"常犯的错误"，归类为 pitfall
- 如果描述的是"评委看重..."、"加分项"、"高分论文的标志"，归类为 signal
- 如果描述的是"我建议..."、"训练方法是..."、"这样教效果好"，归类为 strategy
- 如果描述的是对评分规则的解释，归类为 rubric

输出格式:
{"items": [{"title": "...", "description": "...", "annotation_type": "..."}]}

示例输入:
我这些年辅导ISEF的一些体会。发现获奖学生论文里参考文献密度非常高，一般都在15条/千字以上，而且必须是近三年的高影响力期刊。另外大部分学生被动语态占比超过35%，这在ISEF评审里是严重扣分项。

示例输出:
{"items": [{"title": "获奖者引用密度远超失败者", "description": "ISEF获奖学生论文参考文献密度在15条/千字以上，且必须覆盖近三年高影响力期刊。", "annotation_type": "pattern"}, {"title": "被动语态过高导致扣分", "description": "大部分学生被动语态占比超过35%，这是ISEF评审中的严重扣分项。", "annotation_type": "pitfall"}]}"""


def _build_annotations_from_items(
    items: list[dict],
    author: str,
    competition: str,
    default_anno_type: str = "",
) -> list[ExpertAnnotation]:
    annotations: list[ExpertAnnotation] = []
    for item in items:
        title = item.get("title", "").strip()
        description = item.get("description", "").strip()
        anno_type = item.get("annotation_type", default_anno_type).strip()

        if not title or not description:
            continue
        if anno_type not in ANNOTATION_TYPES:
            if default_anno_type in ANNOTATION_TYPES:
                anno_type = default_anno_type
            else:
                continue

        mapped = _resolve_features(
            explicit_feature="",
            linked_features_str="",
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

    return annotations


async def _call_llm_extract(llm, system_prompt: str, user_text: str) -> list[dict]:
    try:
        result = await llm.chat_json(
            system_prompt=system_prompt,
            user_message=user_text,
            temperature=0.2,
            max_tokens=4096,
        )
        return result.get("items", []) if isinstance(result, dict) else []
    except Exception as exc:
        logger.error(f"LLM extraction failed: {exc}")
        return []


async def _parse_mode2_async(
    text: str, llm, author: str, competition: str
) -> ExpertInsights:
    sections = _split_sections_mode2(text)

    if not sections:
        logger.warning("Mode 2: no matching section headers found")
        return ExpertInsights(competition=competition, authors=[author] if author else [])

    all_annotations: list[ExpertAnnotation] = []

    for anno_type, body in sections:
        user_text = f"annotation_type: {anno_type}\n\n{body}"
        items = await _call_llm_extract(llm, _EXTRACTION_SYSTEM_PROMPT, user_text)
        if not items:
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            if lines:
                items = [{
                    "title": lines[0][:30],
                    "description": "\n".join(lines[:10]),
                    "annotation_type": anno_type,
                }]
        annotations = _build_annotations_from_items(items, author, competition, anno_type)
        all_annotations.extend(annotations)

    logger.info(
        f"Mode 2 parsed: {len(sections)} sections → {len(all_annotations)} annotations"
    )
    return ExpertInsights(
        competition=competition,
        authors=[author] if author else [],
        annotations=all_annotations,
    )


async def _parse_mode1_async(
    text: str, llm, author: str, competition: str
) -> ExpertInsights:
    lines_stripped = "\n".join(
        line for line in text.split("\n")
        if not line.startswith("## ")
    )

    items = await _call_llm_extract(llm, _EXTRACTION_SYSTEM_PROMPT_MODE1, lines_stripped)

    if not items:
        logger.warning("Mode 1: LLM returned no items, falling back to heuristic split")
        paragraphs = [p.strip() for p in lines_stripped.split("\n\n") if p.strip()]
        items = []
        for para in paragraphs:
            if len(para) > 30:
                lines = para.split("\n")
                items.append({
                    "title": lines[0][:30],
                    "description": para[:500],
                    "annotation_type": "pattern",
                })

    annotations = _build_annotations_from_items(items, author, competition)

    logger.info(f"Mode 1 parsed: {len(items)} items → {len(annotations)} annotations")
    return ExpertInsights(
        competition=competition,
        authors=[author] if author else [],
        annotations=annotations,
    )


def parse_freeform_expert_doc(
    file_path: str,
    llm,
) -> ExpertInsights:
    text = _read_expert_text(file_path)
    competition, author = _extract_meta(text)
    mode = detect_mode(text)

    if mode == 3:
        from app.calibration.expert_annotator import parse_expert_document
        return parse_expert_document(file_path)

    if mode == 2:
        logger.info(f"Parsing '{file_path}' as Mode 2 (semi-structured), author={author}")
        return asyncio.run(_parse_mode2_async(text, llm, author, competition))
    else:
        logger.info(f"Parsing '{file_path}' as Mode 1 (freeform), author={author}")
        return asyncio.run(_parse_mode1_async(text, llm, author, competition))
