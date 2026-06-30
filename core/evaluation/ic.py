"""IC 计算与分析"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional


def calc_ic(
    factor: pd.Series,
    forward_return: pd.Series,
    method: str = "spearman",
) -> float:
    """
    截面 IC 计算： "spearman"  或 "pearson" 
    """
    aligned = pd.concat([factor, forward_return], axis=1, join="inner").dropna()
    if len(aligned) < 30:
        return np.nan
    return aligned.iloc[:, 0].corr(aligned.iloc[:, 1], method=method)


def calc_ic_stats(ic_series: pd.Series) -> dict:
    """IC 统计：均值 / 标准差 / IR / 胜率 / t统计量"""
    clean = ic_series.dropna()
    if clean.empty:
        return {
            "ic_mean": np.nan, "ic_std": np.nan, "ic_ir": np.nan,
            "ic_win_rate": np.nan, "ic_t": np.nan, "n": 0,
        }
    mean = clean.mean()
    std = clean.std(ddof=1)
    ir = mean / std if std > 1e-12 else np.nan
    win_rate = (clean > 0).mean()
    t = mean / (std / np.sqrt(len(clean))) if std > 1e-12 else np.nan
    return {
        "ic_mean": mean,
        "ic_std": std,
        "ic_ir": ir,
        "ic_win_rate": win_rate,
        "ic_t": t,
        "n": len(clean),
    }


def compute_ic_series(
    factor_dir: str,
    return_dir: str,
    dates: list,
    factor_col: Optional[str] = None,
    ret_col: str = "pct_chg",
    method: str = "spearman",
) -> pd.DataFrame:
    """
    计算每日 IC 序列
    factor_dir: 因子 CSV 文件目录
    return_dir: 收益数据目录
    dates: 交易日列表
    """
    records = []
    for dt in dates:
        factor_path = Path(factor_dir) / f"{dt}.csv"
        ret_path = Path(return_dir) / f"{dt}.csv"
        if not factor_path.exists() or not ret_path.exists():
            continue

        factor_df = pd.read_csv(factor_path)
        if "code" not in factor_df.columns:
            continue
        factor_df = factor_df.set_index("code")

        ret_df = pd.read_csv(ret_path)
        if "code" not in ret_df.columns or ret_col not in ret_df.columns:
            continue
        ret_series = ret_df.set_index("code")[ret_col].astype(float)

        # 自动选因子列
        cols = [c for c in factor_df.columns if c not in {"code", "date"}]
        if factor_col:
            cols = [factor_col] if factor_col in cols else []

        for col in cols:
            factor_series = factor_df[col].astype(float)
            ic = calc_ic(factor_series, ret_series, method)
            coverage = len(factor_series.dropna().index.intersection(ret_series.dropna().index))
            records.append({"date": dt, "factor": col, "ic": ic, "coverage": coverage})

    return pd.DataFrame(records)


def compute_ic_decay(
    factor_series: pd.Series,
    forward_returns: pd.DataFrame,
    periods: list = [1, 5, 10, 20],
    method: str = "spearman",
) -> dict:
    """
    IC 衰减分析
    forward_returns: 多期 forward return，列名为 fwd_1d, fwd_5d, fwd_10d, fwd_20d
    返回 {period: ic_value} 字典
    """
    decay = {}
    for p in periods:
        col = f"fwd_{p}d"
        if col in forward_returns.columns:
            ic = calc_ic(factor_series, forward_returns[col], method)
            decay[p] = ic
    return decay
