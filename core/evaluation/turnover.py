"""换手率与因子稳定性分析"""
import numpy as np
import pandas as pd


def factor_turnover(
    factor_today: pd.Series,
    factor_prev: pd.Series,
    top_n: int = 50,
) -> float:
    """
    turnover = (今日TopN中不在昨日TopN的数量) / top_n
    """
    today_top = set(factor_today.dropna().nlargest(top_n).index)
    prev_top = set(factor_prev.dropna().nlargest(top_n).index)
    if not prev_top:
        return 1.0
    intersection = today_top & prev_top
    return 1.0 - len(intersection) / len(prev_top)


def factor_autocorr(factor_series: pd.Series, lag: int = 1) -> float:
    """因子自相关"""
    return factor_series.autocorr(lag=lag)


def rank_autocorr(factor_series: pd.Series, lag: int = 1) -> float:
    """截面排序自相关"""
    ranked = factor_series.rank()
    return ranked.autocorr(lag=lag)


def turnover_series(
    factor_daily: dict,
    top_n: int = 50,
) -> pd.Series:
    """
    计算每日换手率序列
    factor_daily: {date: factor_series} 字典
    返回以日期为 index 的换手率 Series
    """
    dates = sorted(factor_daily.keys())
    turnovers = []
    for i, dt in enumerate(dates):
        if i == 0:
            turnovers.append(np.nan)
        else:
            t = factor_turnover(factor_daily[dt], factor_daily[dates[i - 1]], top_n)
            turnovers.append(t)
    return pd.Series(turnovers, index=dates)


def stability_diagnostics(
    ic_series: pd.Series,
    window: int = 60,
) -> pd.DataFrame:
    """滚动窗口 IC 统计,返回滚动 IC 均值、标准差、IR 时间序列"""
    roll_mean = ic_series.rolling(window).mean()
    roll_std = ic_series.rolling(window).std()
    roll_ir = roll_mean / roll_std.replace(0, np.nan)

    return pd.DataFrame({
        "roll_ic_mean": roll_mean,
        "roll_ic_std": roll_std,
        "roll_ic_ir": roll_ir,
    })
