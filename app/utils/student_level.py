"""
学生水平自适应 —— 根据文本复杂度估算学生水平，调整 Agent 反馈粒度。

基于以下指标综合判断：
- 字数 (word_count)
- 平均句长 (avg_sentence_length)
- 词汇多样性 (vocabulary_diversity / TTR)
- 引用密度 (citation_density)

输出三个级别：
- BEGINNER: 反馈以引导为主，解释基本概念，给出具体改写示例
- INTERMEDIATE: 反馈以诊断为主，指出问题并建议方向，部分给出示例
- ADVANCED: 反馈以挑战为主，指出可优化的细节，更多采用提问和对比

用法:
    from app.utils.student_level import estimate_student_level, StudentLevel

    level = estimate_student_level(doc)
    level_context = level.to_prompt_context()
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re


class StudentLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

    def to_prompt_context(self) -> str:
        """生成注入 Agent prompt 的学生水平上下文。"""
        contexts = {
            StudentLevel.BEGINNER: (
                "【学生水平：入门】"
                "该学生处于入门阶段，反馈应以引导和鼓励为主。"
                "1. 每指出一个问题，必须给出具体的改写示例（不要说缺少 evidence，要写出可参考的句式）"
                "2. 使用简洁直接的表达，避免学术术语。如果要用术语，先解释意思"
                "3. 优先解决基础结构问题（章节缺失、论据不足），再考虑优化类建议"
                "4. 反馈结尾列出下一步最应该做的 2-3 件事，给出可操作的优先级"
            ),
            StudentLevel.INTERMEDIATE: (
                "【学生水平：进阶】"
                "该学生处于进阶阶段，反馈应侧重诊断和方向性指导。"
                "1. 指出问题时给出改进方向，重要的问题给出示例"
                "2. 可以用专业术语，但关键概念需要简要说明"
                "3. 平衡基础检查和优化建议"
                "4. 反馈末尾总结当前最大的提升空间在哪里"
            ),
            StudentLevel.ADVANCED: (
                "【学生水平：高级】"
                "该学生处于高级阶段，反馈应侧重于精细优化和深度挑战。"
                "1. 跳过基础语法和格式问题（除非特别严重），聚焦论证深度和原创性"
                "2. 多使用提问式反馈：你可以进一步考虑...、这种写法如果加入X维度会更强"
                "3. 引用该领域的高水平标准作为对比基准（如获奖作品通常在此处...）"
                "4. 对论证提出挑战性问题，帮助学生在答辩或评审中更有准备"
            ),
        }
        return contexts.get(self, "")


@dataclass
class LevelEstimation:
    level: StudentLevel
    word_count: int
    avg_sentence_length: float
    vocabulary_diversity: float
    confidence: str  # low / medium / high

    def to_prompt_context(self) -> str:
        return self.level.to_prompt_context()

    def to_summary(self) -> dict:
        return {
            "level": self.level.value,
            "word_count": self.word_count,
            "avg_sentence_length": round(self.avg_sentence_length, 1),
            "vocabulary_diversity": round(self.vocabulary_diversity, 3),
            "confidence": self.confidence,
        }


def estimate_student_level(text: str) -> LevelEstimation:
    """根据文本特征估算学生水平。

    使用启发式规则，无需 LLM 调用。
    """
    if not text or not text.strip():
        return LevelEstimation(
            level=StudentLevel.BEGINNER,
            word_count=0,
            avg_sentence_length=0,
            vocabulary_diversity=0,
            confidence="low",
        )

    # Word count
    words = re.findall(r"[a-zA-Z]+", text)
    word_count = len(words)

    # Average sentence length
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    if sentences:
        total_words_in_sentences = sum(len(re.findall(r"[a-zA-Z]+", s)) for s in sentences)
        avg_sentence_length = total_words_in_sentences / len(sentences)
    else:
        avg_sentence_length = 0

    # Vocabulary diversity (Type-Token Ratio)
    if words:
        vocab_diversity = len(set(w.lower() for w in words)) / len(words)
    else:
        vocab_diversity = 0

    # Scoring: each factor contributes
    score = 0

    # Word count: <400 → 0, 400-1200 → 1, 1200-3000 → 2, >3000 → 3
    if word_count >= 3000:
        score += 3
    elif word_count >= 1200:
        score += 2
    elif word_count >= 400:
        score += 1

    # Avg sentence length: <12 → 0, 12-18 → 1, 18-25 → 2, >25 → 3
    if avg_sentence_length >= 25:
        score += 3
    elif avg_sentence_length >= 18:
        score += 2
    elif avg_sentence_length >= 12:
        score += 1

    # Vocabulary diversity: TTR naturally decreases with text length (Zipf's law)
    # <0.06 → 0, 0.06-0.12 → 1, 0.12-0.20 → 2, >0.20 → 3
    if vocab_diversity >= 0.20:
        score += 3
    elif vocab_diversity >= 0.12:
        score += 2
    elif vocab_diversity >= 0.06:
        score += 1

    # Determine level
    # Very short texts (<100 words) are always BEGINNER regardless of TTR
    if word_count < 100:
        level = StudentLevel.BEGINNER
        confidence = "low"
    elif score >= 6:
        level = StudentLevel.ADVANCED
        confidence = "high" if score >= 7 else "medium"
    elif score >= 3:
        level = StudentLevel.INTERMEDIATE
        confidence = "high" if score >= 5 else "medium"
    else:
        level = StudentLevel.BEGINNER
        confidence = "medium" if score >= 1 else "low"

    return LevelEstimation(
        level=level,
        word_count=word_count,
        avg_sentence_length=avg_sentence_length,
        vocabulary_diversity=vocab_diversity,
        confidence=confidence,
    )
