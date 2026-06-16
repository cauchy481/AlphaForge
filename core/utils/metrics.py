"""通用金融指标计算"""
import numpy as np
import pandas as pd


def max_drawdown(returns: pd.Series) -> float:
    """计算收益率序列的最大回撤"""
    if returns.empty:
        return np.nan
    cumulative = (1 + returns).cumprod()
    peak = cumulative.cummax()
    drawdown = cumulative / peak - 1
    return float(drawdown.min())


def annual_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    """年化收益率"""
    if returns.empty:
        return np.nan
    total = (1 + returns).prod()
    return float(total ** (periods_per_year / len(returns)) - 1)


def annual_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """年化波动率"""
    if returns.empty:
        return np.nan
    return float(returns.std() * np.sqrt(periods_per_year))


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.03,
    periods_per_year: int = 252,
) -> float:
    """夏普比率"""
    if returns.empty:
        return np.nan
    excess = annual_return(returns, periods_per_year) - risk_free_rate
    vol = annual_volatility(returns, periods_per_year)
    return excess / vol if vol > 0 else 0.0


def calmar_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    """卡玛比率 = 年化收益 / |最大回撤|"""
    ann = annual_return(returns, periods_per_year)
    mdd = max_drawdown(returns)
    if np.isnan(mdd) or mdd == 0:
        return np.nan
    return ann / abs(mdd)


def win_rate(returns: pd.Series) -> float:
    """盈利日占比"""
    if returns.empty:
        return np.nan
    return float((returns > 0).mean())


def information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """信息比率 = mean(超额收益) / std(超额收益) * sqrt(252)"""
    excess = returns - benchmark_returns
    if excess.std() == 0:
        return 0.0
    return float(excess.mean() / excess.std() * np.sqrt(252))


def rolling_sharpe(returns: pd.Series, window: int = 60) -> pd.Series:
    """滚动夏普比率"""
    roll_mean = returns.rolling(window).mean()
    roll_std = returns.rolling(window).std()
    return (roll_mean / roll_std.replace(0, np.nan)) * np.sqrt(252)
