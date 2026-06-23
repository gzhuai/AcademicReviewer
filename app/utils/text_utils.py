"""文本处理工具 —— annotation_builder 和 docx_exporter 共享。

包含段落分割和位置解析两个共用函数。
"""

import re


def split_paragraphs(text: str) -> list[str]:
    """按空行分割段落，保留非空段落。"""
    if not text:
        return []
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip()]


def parse_location(loc: str) -> int:
    """解析 '第X段' 样式的位置文字，返回 0-based 段落索引。"""
    m = re.search(r"第\s*(\d+)\s*段", str(loc))
    if m:
        return int(m.group(1)) - 1
    return -1
