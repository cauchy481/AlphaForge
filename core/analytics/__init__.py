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
    基于因子贡献的绩效归因。

    总超额收益 = 因子配置收益 + 残差选股收益

    - factor_allocation: 各因子贡献之和，即因子驱动的超额部分
    - residual_selection: 总超额中扣除因子贡献后的残差，对应个股选择和模型外信息
    - contributions: 各因子单独贡献 Series

    注意：这不是严格的 Brinson-Hood-Beebower 模型（需要分行业权重和收益），
    而是因子层面的线性归因分解。
    """
    total_excess = portfolio_return - benchmark_return
    factor_allocation = float(factor_contributions.sum())
    residual_selection = total_excess - factor_allocation

    return {
        "total_excess": total_excess,
        "factor_allocation": factor_allocation,
        "residual_selection": residual_selection,
        "contributions": factor_contributions,
    }
