"""归因分析模块"""
import pandas as pd
from typing import Dict


def factor_contribution(
    weights: pd.Series,
    factor_gaps: pd.Series,
) -> pd.Series:
    """
    因子贡献分解：Contribution_i = Weight_i * Gap_i
    gap_i = 多头组因子均值 - 空头组因子均值
    """
    aligned_w = weights.reindex(factor_gaps.index).fillna(0.0)
    return aligned_w * factor_gaps


def brinson_attribution(
    portfolio_return: float,
    benchmark_return: float,
    factor_contributions: pd.Series,
) -> Dict:
    """
    简化版 Brinson 归因
    总超额收益 = 配置收益 + 选股收益 + 交互项
    """
    total_excess = portfolio_return - benchmark_return
    allocation = factor_contributions.sum()
    selection = portfolio_return - allocation
    interaction = total_excess - allocation - selection

    return {
        "total_excess": total_excess,
        "factor_allocation": allocation,
        "stock_selection": selection,
        "interaction": interaction,
        "contributions": factor_contributions,
    }
