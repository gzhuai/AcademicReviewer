import json
from datetime import datetime

from app.calibration.cohens_d import EffectSizeResult, CrossValidationResult
from app.calibration.diff_generator import ConfigChange


def generate_calibration_report(
    competition: str,
    competition_type: str,
    effect_sizes: list[EffectSizeResult],
    cross_validations: list[CrossValidationResult],
    config_changes: list[ConfigChange],
    config_diff: list[dict] | None = None,
    n_winners: int = 0,
    n_losers: int = 0,
    n_external: int = 0,
    expert_insights_report: str | None = None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append(f"# 校准报告: {competition}")
    lines.append(f"")
    lines.append(f"**生成时间**: {now}  ")
    lines.append(f"**竞赛类型**: {competition_type}  ")
    lines.append(f"**样本量**: 我方获奖 {n_winners} 篇 | 我方失败 {n_losers} 篇 | 外部获奖 {n_external} 篇  ")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    lines.append(f"## 1. 效应量摘要 (Cohen's d)")
    lines.append(f"")
    lines.append(f"| 特征 | Cohen's d | |d| | 效应等级 | 信号方向 | 置信度 | 获奖组 M | 失败组 M |")
    lines.append(f"|------|-----------|-----|----------|----------|--------|----------|----------|")
    for es in effect_sizes:
        sig = "+" if es.signal_type == "正向" else "−"
        lines.append(
            f"| {es.feature_name} | {es.d_value:.3f} | {es.d_absolute:.3f} | "
            f"{es.label} | {sig} | {es.confidence} | "
            f"{es.mean_winners:.4f} | {es.mean_losers:.4f} |"
        )
    lines.append(f"")

    critical_count = sum(1 for es in effect_sizes if es.category == "critical")
    major_count = sum(1 for es in effect_sizes if es.category == "major")
    minor_count = sum(1 for es in effect_sizes if es.category == "minor")
    lines.append(f"**效应分布**: 大效应 {critical_count} | 中效应 {major_count} | 小效应 {minor_count}")
    lines.append(f"")

    positive_signals = [es for es in effect_sizes if es.signal_type == "正向" and es.category in ("critical", "major")]
    negative_signals = [es for es in effect_sizes if es.signal_type == "负向" and es.category in ("critical", "major")]

    if positive_signals:
        lines.append(f"###  正向信号（获奖者显著更强）")
        for ps in positive_signals:
            lines.append(f"- **{ps.feature_name}**: d = {ps.d_value:.3f} ({ps.label})，置信度: {ps.confidence}")
        lines.append(f"")

    if negative_signals:
        lines.append(f"###  负向信号（失败者显著缺乏）")
        for ns in negative_signals:
            lines.append(f"- **{ns.feature_name}**: d = {ns.d_value:.3f} ({ns.label})，置信度: {ns.confidence}")
        lines.append(f"")

    if cross_validations:
        lines.append(f"## 2. 交叉验证")
        lines.append(f"")
        lines.append(f"| 特征 | 内部 d (W vs L) | 外部 d (W vs Ext) | 一致性 | 置信度 |")
        lines.append(f"|------|-----------------|-------------------|--------|--------|")
        for cv in cross_validations:
            lines.append(
                f"| {cv.feature_name} | {cv.d_my_winners_vs_losers:.3f} | "
                f"{cv.d_my_winners_vs_external:.3f} | {cv.agreement} | {cv.confidence} |"
            )
        lines.append(f"")

    if config_changes:
        lines.append(f"## 3. 建议配置更新")
        lines.append(f"")

        new_items = [c for c in config_changes if "新增" in c.change_type]
        adjustments = [c for c in config_changes if "参数调整" in c.change_type]

        if new_items:
            lines.append(f"### 3.1 新增配置项")
            for i, c in enumerate(new_items, 1):
                lines.append(f"**{i}. {c.path}**")
                lines.append(f"- 操作: {c.change_type}")
                lines.append(f"- 新值: {c.new_value}")
                lines.append(f"- 原因: {c.reason}")
                lines.append(f"- 效应量: |d| = {c.effect_size:.3f}，置信度: {c.confidence}")
                lines.append(f"")

        if adjustments:
            lines.append(f"### 3.2 参数调整")
            for i, c in enumerate(adjustments, 1):
                lines.append(f"**{i}. {c.path}**")
                lines.append(f"- 操作: {c.change_type}")
                lines.append(f"- 旧值: {c.old_value}")
                lines.append(f"- 新值: {c.new_value}")
                lines.append(f"- 原因: {c.reason}")
                lines.append(f"- 效应量: |d| = {c.effect_size:.3f}，置信度: {c.confidence}")
                lines.append(f"")

    if config_diff:
        lines.append(f"## 4. 配置文件 Diff")
        lines.append(f"")
        lines.append(f"| 路径 | 变更类型 | 旧值 | 新值 |")
        lines.append(f"|------|----------|------|------|")
        for d in config_diff:
            old_s = d["old"][:60] + ("..." if len(d["old"]) > 60 else "")
            new_s = d["new"][:60] + ("..." if len(d["new"]) > 60 else "")
            lines.append(f"| {d['path']} | {d['type']} | {old_s} | {new_s} |")
        lines.append(f"")

    lines.append(f"## 5. 人工审核清单")
    lines.append(f"")
    lines.append(f"> 以下项目需要人工逐一确认后，才可将配置更新合并到主配置文件。")
    lines.append(f"")

    for i, c in enumerate(config_changes, 1):
        lines.append(f"- [ ] **{c.path}** — {c.change_type}")
        lines.append(f"  - 理由: {c.reason}")
        lines.append(f"  - 确认人: ________  日期: ________")
        lines.append(f"  - 备注: ________")
        lines.append(f"")

    if expert_insights_report:
        lines.append(expert_insights_report)
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*报告由 AcademicReviewer Calibration Engine 自动生成*")

    return "\n".join(lines)
