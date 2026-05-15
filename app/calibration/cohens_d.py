import math
from dataclasses import dataclass


@dataclass
class EffectSizeResult:
    feature_name: str
    d_value: float
    d_absolute: float
    category: str
    label: str
    mean_winners: float
    mean_losers: float
    sd_pooled: float
    confidence: str
    signal_type: str
    notes: str = ""


@dataclass
class CrossValidationResult:
    feature_name: str
    d_my_winners_vs_losers: float
    d_my_winners_vs_external: float
    agreement: str
    confidence: str


def cohens_d(group_a: list[float], group_b: list[float]) -> tuple[float, float, float, float]:
    na = len(group_a)
    nb = len(group_b)
    if na < 2 or nb < 2:
        return 0.0, 0.0, 0.0, 0.0

    mean_a = sum(group_a) / na
    mean_b = sum(group_b) / nb

    if na > 1:
        var_a = sum((x - mean_a) ** 2 for x in group_a) / (na - 1)
    else:
        var_a = 0.0

    if nb > 1:
        var_b = sum((x - mean_b) ** 2 for x in group_b) / (nb - 1)
    else:
        var_b = 0.0

    df = na + nb - 2
    if df <= 0:
        return 0.0, mean_a, mean_b, 0.0

    sd_pooled = math.sqrt(((na - 1) * var_a + (nb - 1) * var_b) / df)
    if sd_pooled == 0:
        return 0.0, mean_a, mean_b, 0.0

    d = (mean_a - mean_b) / sd_pooled
    return d, mean_a, mean_b, sd_pooled


def categorize_effect(d: float) -> tuple[str, str]:
    d_abs = abs(d)
    if d_abs >= 0.8:
        return "critical", "大效应"
    elif d_abs >= 0.5:
        return "major", "中效应"
    elif d_abs >= 0.2:
        return "minor", "小效应"
    else:
        return "none", "无差异"


def compute_effect_sizes(
    winners_features: list[dict],
    losers_features: list[dict],
    feature_names: list[str],
) -> list[EffectSizeResult]:
    results = []

    for fname in feature_names:
        winner_vals = [d[fname] for d in winners_features if fname in d and isinstance(d[fname], (int, float))]
        loser_vals = [d[fname] for d in losers_features if fname in d and isinstance(d[fname], (int, float))]

        if not winner_vals or not loser_vals:
            continue

        d_val, mean_w, mean_l, sd_pooled = cohens_d(winner_vals, loser_vals)
        category, label = categorize_effect(d_val)

        n_total = len(winner_vals) + len(loser_vals)
        if n_total < 5:
            conf = "极低"
        elif n_total < 10:
            conf = "低"
        elif n_total < 20:
            conf = "中"
        else:
            conf = "高"

        signal = "正向" if d_val > 0 else "负向"

        results.append(EffectSizeResult(
            feature_name=fname,
            d_value=round(d_val, 3),
            d_absolute=round(abs(d_val), 3),
            category=category,
            mean_winners=round(mean_w, 4),
            mean_losers=round(mean_l, 4),
            sd_pooled=round(sd_pooled, 4),
            confidence=conf,
            signal_type=signal,
            label=label,
        ))

    results.sort(key=lambda r: r.d_absolute, reverse=True)
    return results


def cross_validate(
    my_winners: list[dict],
    my_losers: list[dict],
    external_winners: list[dict],
    feature_names: list[str],
) -> list[CrossValidationResult]:
    results = []

    for fname in feature_names:
        w_vals = [d[fname] for d in my_winners if fname in d and isinstance(d[fname], (int, float))]
        l_vals = [d[fname] for d in my_losers if fname in d and isinstance(d[fname], (int, float))]
        e_vals = [d[fname] for d in external_winners if fname in d and isinstance(d[fname], (int, float))]

        if not w_vals or not l_vals:
            continue

        d_my, _, _, _ = cohens_d(w_vals, l_vals)

        if not e_vals or len(e_vals) < 2:
            agreement = "无外部样本"
            confidence = "仅内部"
            d_ext = 0.0
        else:
            d_ext, _, _, _ = cohens_d(w_vals, e_vals)
            diff = abs(abs(d_my) - abs(d_ext))
            if diff < 0.3:
                agreement = "一致"
                confidence = "高"
            elif diff < 0.6:
                agreement = "部分一致"
                confidence = "中"
            else:
                agreement = "不一致"
                confidence = "低"

        results.append(CrossValidationResult(
            feature_name=fname,
            d_my_winners_vs_losers=round(d_my, 3),
            d_my_winners_vs_external=round(d_ext if e_vals else 0, 3),
            agreement=agreement,
            confidence=confidence,
        ))

    results.sort(key=lambda r: abs(r.d_my_winners_vs_losers), reverse=True)
    return results
