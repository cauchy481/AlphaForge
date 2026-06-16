"""多因子权重计算"""
import numpy as np
import pandas as pd
from typing import List


def normalize_weights(weights: pd.Series, clip_negative: bool = True) -> pd.Series:
    """权重归一化"""
    w = weights.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)
    if clip_negative:
        w = w.clip(lower=0)
    total = w.abs().sum()
    if total == 0:
        return pd.Series(1.0 / len(w), index=w.index)
    return w / total


def equal_weight(factor_names: List[str]) -> pd.Series:
    """等权"""
    n = len(factor_names)
    return pd.Series(1.0 / n, index=factor_names)


def ic_weight(ic_means: pd.Series) -> pd.Series:
    """IC 加权"""
    signed = ic_means.copy()
    return normalize_weights(signed, clip_negative=False)


def icir_weight(ic_means: pd.Series, ic_stds: pd.Series) -> pd.Series:
    """ICIR 加权"""
    ir = ic_means / ic_stds.replace(0, np.nan)
    return normalize_weights(ir, clip_negative=False)


def ret_spread_weight(spreads: pd.Series) -> pd.Series:
    """收益差加权"""
    return normalize_weights(spreads, clip_negative=False)


def compute_factor_metrics(
    panel: pd.DataFrame,
    factor_cols: List[str],
    ret_col: str = "ret",
    n_groups: int = 10,
) -> pd.DataFrame:
    """
    从面板数据计算因子绩效指标
    panel: 含 date, code 和多列因子及 ret_col 的 DataFrame
    返回每个因子的 ic_mean, ic_std, ic_ir, ret_spread
    """
    records = []
    for col in factor_cols:
        subset = panel[["date", col, ret_col]].dropna()
        if subset.empty:
            records.append({"factor": col, "ic_mean": np.nan, "ic_std": np.nan, "ic_ir": np.nan, "ret_spread": np.nan})
            continue
        # 计算每日 IC
        daily_ic = []
        for _, grp in subset.groupby("date"):
            if len(grp) < 30:
                continue
            ic = grp[col].corr(grp[ret_col], method="spearman")
            daily_ic.append(ic)
        ic_series = pd.Series(daily_ic)
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        ic_ir_val = ic_mean / ic_std if ic_std > 0 else np.nan

        # 分组收益差（简化：全样本聚合）
        factor = subset[col]
        fwd = subset[ret_col]
        try:
            ranked = factor.rank(method="first")
            groups = pd.qcut(ranked, q=n_groups, labels=range(1, n_groups + 1), duplicates="drop")
            grp_ret = fwd.groupby(groups).mean()
            spread = float(grp_ret.iloc[-1] - grp_ret.iloc[0]) if len(grp_ret) >= 2 else np.nan
        except Exception:
            spread = np.nan

        records.append({"factor": col, "ic_mean": ic_mean, "ic_std": ic_std, "ic_ir": ic_ir_val, "ret_spread": spread})

    return pd.DataFrame(records).set_index("factor")


def build_composite(
    panel: pd.DataFrame,
    factor_cols: List[str],
    weights: pd.Series,
) -> pd.DataFrame:
    """
    构建合成因子
    返回 DataFrame 含 date, code, composite 
    """
    w = weights.reindex(factor_cols).fillna(0.0)
    composites = []
    for dt, grp in panel.groupby("date"):
        values = grp[factor_cols].values
        scores = values @ w.values
        result = grp[["code"]].copy()
        result["date"] = dt
        result["composite"] = scores
        composites.append(result)
    if not composites:
        return pd.DataFrame(columns=["date", "code", "composite"])
    return pd.concat(composites, ignore_index=True)
