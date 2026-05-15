"""
端到端测试脚本 v0.2
验证：上传一篇 ISEF 论文 → 5 Agent 2 轮并行审查 → 获得完整结构化审查报告

使用方法：
  1. 先在 .env 中填入至少一个 LLM 的 API Key
  2. uv run python tests/test_e2e.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm.base import LLMFactory
from app.config import settings
from app.orchestrator import Orchestrator


async def main():
    if not _has_api_key():
        print("\u274c 未配置 API Key。请在 .env 文件中设置至少一个 LLM 的 API Key。")
        print(f"   当前配置：")
        print(f"   LLM_PROVIDER = {settings.llm_provider}")
        return

    print(f"\U0001f680 使用 {settings.llm_provider} 模型进行 5 Agent 端到端测试\n")

    llm = LLMFactory.create(settings.llm_provider)
    orch = Orchestrator(llm)

    test_file = Path(__file__).parent / "fixtures" / "sample_isef_paper.txt"
    print(f"\U0001f4c4 测试稿件: {test_file}")
    print(f"\U0001f3c6 竞赛: ISEF")
    print(f"\U0001f4cb 预期 Agent: A1 Rubric → A2 Structure → A3 Argument → A4 Language → A5 Integrity")
    print("-" * 60)

    try:
        report = await orch.review(file_path=str(test_file), competition="ISEF")
    except Exception as e:
        print(f"\u274c 审查失败: {e}")
        return

    print("\n" + "=" * 60)
    print("完整审查报告")
    print("=" * 60)

    print(f"\n\u23f1 总耗时: {report.meta.get('duration_seconds', 'N/A')}s")
    print(f"\U0001f4ca 字数: {report.meta.get('word_count', 'N/A')}")
    print(f"\U0001f916 模型: {report.meta.get('model', 'N/A')}")
    print(f"\U0001f4ca 综合得分: {report.total_score}")
    print(f"  Agent 分项得分:")
    for agent_name, score in report.scores.items():
        print(f"    {agent_name}: {score}/10")

    _print_section("A1 Rubric Parser", report.rubric)
    _print_section("A2 Structure & Logic", report.structure)
    _print_section("A3 Argument & Evidence", report.argument)
    _print_section("A4 Language & Style", report.language)
    _print_section("A5 Academic Integrity", report.integrity)

    if report.errors:
        print(f"\n\u26a0\ufe0f 审查过程中出现错误:")
        for e in report.errors:
            print(f"  \u00b7 {e}")

    print("\n" + "=" * 60)
    agent_count = sum(1 for v in [report.rubric, report.structure, report.argument, report.language, report.integrity] if v)
    print(f"\u2705 5 Agent 端到端测试完成 ({agent_count}/5 Agent 返回结果)")


def _print_section(title: str, data: dict | None):
    if data is None:
        print(f"\n--- {title} ---")
        print("  \u26a0\ufe0f 未获得结果")
        return

    print(f"\n--- {title} ---")
    if data.get("error"):
        print(f"  \u26a0\ufe0f 错误: {data['error']}")
        return

    score = _extract_score(data)
    if score is not None:
        print(f"  \U0001f4ca 评分: {score}/10")

    if data.get("positive_points"):
        pts = data["positive_points"][:3]
        print(f"  \u2705 优点: {'; '.join(pts)}")

    if data.get("key_issues"):
        issues = data["key_issues"][:3]
        print(f"  \u26a0\ufe0f 问题: {'; '.join(issues)}")

    if title == "A4 Language & Style":
        rewrites = data.get("rewrites", [])
        suggestions = data.get("suggestions", [])
        if rewrites:
            print(f"  [REWRITE] 改写 ({len(rewrites)} 处):")
            for rw in rewrites[:2]:
                print(f"    \u00b7 {rw.get('location', '?')}: {rw.get('original', '?')[:50]}... → {rw.get('corrected', '?')[:50]}...")
        if suggestions:
            print(f"  [SUGGEST] 建议 ({len(suggestions)} 处):")
            for sg in suggestions[:2]:
                print(f"    \u00b7 {sg.get('location', '?')} [{sg.get('type', '?')}]: {sg.get('description', '?')[:70]}")


def _extract_score(data: dict) -> float | None:
    candidates = [
        "rubric_score", "structure_score", "overall_score",
        "language_score", "integrity_score",
        "argument_score", "evidence_score",
    ]
    for key in candidates:
        if key in data:
            try:
                return float(data[key])
            except (ValueError, TypeError):
                continue

    summary = data.get("summary", {})
    if isinstance(summary, dict):
        for key in ["overall_language_score", "total_score"]:
            if key in summary:
                try:
                    return float(summary[key])
                except (ValueError, TypeError):
                    continue
    return None


def _has_api_key() -> bool:
    provider = settings.llm_provider
    key_map = {
        "openai": settings.openai_api_key,
        "gemini": settings.gemini_api_key,
        "deepseek": settings.deepseek_api_key,
        "glm": settings.glm_api_key,
    }
    return bool(key_map.get(provider) and key_map[provider] not in ("", "sk-xxx", "xxx"))


if __name__ == "__main__":
    asyncio.run(main())
