import json
from dataclasses import dataclass, field


@dataclass
class ConfigChange:
    path: str
    change_type: str
    old_value: str
    new_value: str
    reason: str = ""
    effect_size: float = 0.0
    confidence: str = ""


def generate_rule_updates(
    effect_sizes: list,
    feature_names: list[str],
    config_feature_mapping: dict[str, str],
    current_config: dict,
) -> list[ConfigChange]:
    changes = []

    for es in effect_sizes:
        if es.category == "none":
            continue

        config_path = config_feature_mapping.get(es.feature_name)
        if not config_path:
            continue

        old_val = _get_nested_value(current_config, config_path)
        if old_val is None:
            change_type = "新增"
        else:
            change_type = "参数调整"

        reason = (
            f"获奖组均值 {es.mean_winners} vs 失败组均值 {es.mean_losers}，"
            f"Cohen's d = {es.d_value}（{es.label}），置信度：{es.confidence}"
        )

        changes.append(ConfigChange(
            path=config_path,
            change_type=change_type,
            old_value=str(old_val) if old_val is not None else "(无)",
            new_value=f"建议阈值: winners M={es.mean_winners:.4f}",
            reason=reason,
            effect_size=es.d_absolute,
            confidence=es.confidence,
        ))

    return changes


def generate_fatal_defect_updates(
    effect_sizes: list,
    losers_features: list[dict],
    winners_features: list[dict],
    current_config: dict,
) -> list[ConfigChange]:
    changes = []

    binary_features = [
        "has_p_value", "has_effect_size", "has_control_group",
        "has_sample_size", "gap_statement_present",
        "limitations_section_present",
    ]

    for es in effect_sizes:
        if es.feature_name not in binary_features:
            continue
        if es.signal_type != "负向":
            continue
        if es.category not in ("critical", "major"):
            continue

        loser_rate = sum(1 for d in losers_features if d.get(es.feature_name, 0) < 0.5) / max(len(losers_features), 1)
        winner_rate = sum(1 for d in winners_features if d.get(es.feature_name, 0) < 0.5) / max(len(winners_features), 1)

        if loser_rate - winner_rate > 0.15:
            existing_defects = current_config.get("fatal_defects", [])
            already_exists = any(
                d.get("id") == f"missing_{es.feature_name}" for d in existing_defects
            )
            change_type = "参数调整" if already_exists else "新增 fatal_defect"

            changes.append(ConfigChange(
                path=f"fatal_defects.missing_{es.feature_name}",
                change_type=change_type,
                old_value="已存在" if already_exists else "(无)",
                new_value=f"loser_rate={loser_rate:.0%}, winner_rate={winner_rate:.0%}",
                reason=(
                    f"失败文章 {loser_rate:.0%} 缺少 {es.feature_name}，"
                    f"获奖文章仅 {winner_rate:.0%}，Cohen's d = {es.d_value}"
                ),
                effect_size=es.d_absolute,
                confidence=es.confidence,
            ))

    return changes


def diff_configs(old_config: dict, new_config: dict) -> list[dict]:
    diffs = []

    def _diff_recursive(old: dict | list, new: dict | list, path: str = ""):
        if isinstance(old, dict) and isinstance(new, dict):
            all_keys = set(old) | set(new)
            for key in sorted(all_keys):
                sub_path = f"{path}.{key}" if path else key
                if key not in old:
                    diffs.append({"path": sub_path, "type": "新增键", "old": "(无)", "new": json.dumps(new[key], ensure_ascii=False)})
                elif key not in new:
                    diffs.append({"path": sub_path, "type": "删除键", "old": json.dumps(old[key], ensure_ascii=False), "new": "(无)"})
                else:
                    _diff_recursive(old[key], new[key], sub_path)
        elif isinstance(old, list) and isinstance(new, list):
            max_len = max(len(old), len(new))
            for i in range(max_len):
                sub_path = f"{path}[{i}]"
                if i >= len(old):
                    diffs.append({"path": sub_path, "type": "新增元素", "old": "(无)", "new": json.dumps(new[i], ensure_ascii=False)})
                elif i >= len(new):
                    diffs.append({"path": sub_path, "type": "删除元素", "old": json.dumps(old[i], ensure_ascii=False), "new": "(无)"})
                else:
                    _diff_recursive(old[i], new[i], sub_path)
        elif old != new:
            diffs.append({"path": path, "type": "值变更", "old": str(old), "new": str(new)})

    _diff_recursive(old_config, new_config)
    return diffs


def _get_nested_value(data: dict, path: str):
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
