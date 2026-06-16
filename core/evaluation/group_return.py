"""分组回测与单调性检验"""
import numpy as np
import pandas as pd


def assign_groups(factor: pd.Series, n_groups: int = 10) -> pd.Series:
    """按因子值等分分组"""
    ranked = factor.rank(method="first")
    try:
        groups = pd.qcut(ranked, q=n_groups, labels=range(1, n_groups + 1))
    except ValueError:
        return pd.Series(np.nan, index=factor.index)
    return groups.astype(float)


def group_returns(
    factor: pd.Series,
    forward_return: pd.Series,
    n_groups: int = 10,
) -> pd.Series:
    """计算各分组的等权平均收益，返回 Series(index=组号, value=平均收益)"""
    aligned = pd.concat([factor.rename("factor"), forward_return.rename("ret")], axis=1).dropna()
    if aligned.empty:
        return pd.Series(dtype=float)

    aligned["group"] = assign_groups(aligned["factor"], n_groups)
    result = aligned.groupby("group")["ret"].mean()
    return result.reindex(range(1, n_groups + 1))


def long_short_spread(group_ret: pd.Series) -> float:
    """多空收益差：最高组 - 最低组"""
    if group_ret.empty or len(group_ret) < 2:
        return np.nan
    n = group_ret.index.max()
    return float(group_ret[n] - group_ret[1])


def monotonicity(group_ret: pd.Series) -> float:
    """单调性检验：组号与组收益的 Spearman 秩相关"""
    valid = group_ret.dropna()
    if len(valid) < 3:
        return np.nan
    return valid.corr(pd.Series(valid.index), method="spearman")


def run_group_backtest(
    factor_df: pd.DataFrame,
    ret_df: pd.DataFrame,
    factor_col: str,
    ret_col: str = "pct_chg",
    n_groups: int = 10,
) -> dict:
    """
    factor_df: index=code, 含因子列
    ret_df: index=code, 含收益列
    返回分组收益和多空差
    """
    factor = factor_df[factor_col].astype(float)
    fwd_ret = ret_df[ret_col].astype(float)

    gr = group_returns(factor, fwd_ret, n_groups)
    spread = long_short_spread(gr)
    mono = monotonicity(gr)

    return {
        "group_returns": gr,
        "long_short_spread": spread,
        "monotonicity": mono,
    }
