"""综合评估报告"""
import numpy as np
import pandas as pd
from typing import Dict, Optional
from .ic import calc_ic_stats
from .turnover import stability_diagnostics


def generate_factor_scorecard(
    factor_name: str,
    category: str,
    ic_series: pd.Series,
    group_ret: pd.Series = None,
    turnovers: pd.Series = None,
) -> Dict:
    """生成单个因子的评分卡"""
    ic_stats = calc_ic_stats(ic_series)

    scorecard = {
        "factor": factor_name,
        "category": category,
        "ic_mean": ic_stats["ic_mean"],
        "ic_std": ic_stats["ic_std"],
        "ic_ir": ic_stats["ic_ir"],
        "ic_win_rate": ic_stats["ic_win_rate"],
        "ic_t": ic_stats["ic_t"],
        "n_days": ic_stats["n"],
    }

    if group_ret is not None and not group_ret.empty:
        n = group_ret.index.max()
        scorecard["long_short_spread"] = float(group_ret[n] - group_ret[1]) if n >= 2 else np.nan
        scorecard["top_return"] = float(group_ret[n])
        scorecard["bottom_return"] = float(group_ret[1])
    else:
        scorecard["long_short_spread"] = np.nan
        scorecard["top_return"] = np.nan
        scorecard["bottom_return"] = np.nan

    if turnovers is not None and not turnovers.empty:
        scorecard["avg_turnover"] = float(turnovers.mean())
        scorecard["turnover_std"] = float(turnovers.std())
    else:
        scorecard["avg_turnover"] = np.nan
        scorecard["turnover_std"] = np.nan

    scorecard["rating"] = _assign_rating(ic_stats)

    return scorecard


def _assign_rating(ic_stats: dict) -> str:
    """根据 IC 统计给出综合评级"""
    ir = ic_stats.get("ic_ir", np.nan)
    t = ic_stats.get("ic_t", np.nan)
    win_rate = ic_stats.get("ic_win_rate", np.nan)

    score = 0
    if abs(ir) > 0.75:
        score += 3
    elif abs(ir) > 0.5:
        score += 2
    elif abs(ir) > 0.3:
        score += 1
    if t > 3.0:
        score += 2
    elif t > 2.0:
        score += 1
    if win_rate > 0.58:
        score += 2
    elif win_rate > 0.53:
        score += 1

    if score >= 6:
        return "A"
    elif score >= 4:
        return "B"
    elif score >= 2:
        return "C"
    return "D"


def compare_factors(scorecards: list) -> pd.DataFrame:
    """多因子对比矩阵"""
    df = pd.DataFrame(scorecards)
    cols = ["factor", "category", "ic_mean", "ic_ir", "ic_win_rate",
            "long_short_spread", "avg_turnover", "rating"]
    return df[[c for c in cols if c in df.columns]]


def compute_composite_score(
    ic_mean: float,
    ic_ir: float,
    monotonicity: float = 0.0,
    turnover: float = 0.5,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    
    if weights is None:
        weights = {"ic_ir": 0.40, "ic_mean": 0.20, "mono": 0.20, "stability": 0.20}

    score = 0.0
    if np.isfinite(ic_mean):
        score += weights.get("ic_mean", 0.20) * ic_mean
    if np.isfinite(ic_ir):
        score += weights.get("ic_ir", 0.40) * ic_ir
    if np.isfinite(monotonicity):
        score += weights.get("mono", 0.20) * monotonicity
    if np.isfinite(turnover):
        stability = 1.0 - turnover
        score += weights.get("stability", 0.20) * stability

    return score


def build_factor_timing(
    ic_series: pd.Series,
    window: int = 20,
    ir_threshold: float = 0.2,
    min_periods: Optional[int] = None,
) -> pd.DataFrame:
    
    if min_periods is None:
        min_periods = max(window // 2, 10)

    clean = ic_series.dropna()
    if len(clean) < min_periods:
        return pd.DataFrame(columns=["date", "ic", "roll_ic_mean", "roll_ic_std", "roll_ic_ir", "factor_on"])

    roll_mean = clean.rolling(window, min_periods=min_periods).mean()
    roll_std = clean.rolling(window, min_periods=min_periods).std()
    roll_ir = roll_mean / roll_std.replace(0, np.nan)

    factor_on = ((roll_mean > 0) & (roll_ir > ir_threshold)).astype(int)

    timing = pd.DataFrame({
        "date": clean.index,
        "ic": clean.values,
        "roll_ic_mean": roll_mean.values,
        "roll_ic_std": roll_std.values,
        "roll_ic_ir": roll_ir.values,
        "factor_on": factor_on.values,
    })

    # 对齐日期
    timing["date"] = pd.to_datetime(timing["date"], errors="coerce")
    return timing.sort_values("date").reset_index(drop=True)
