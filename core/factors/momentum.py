"""动量类因子"""
import numpy as np
import pandas as pd
from .registry import FactorRegistry


@FactorRegistry.register(
    name="momentum_20d",
    category="momentum",
    description="20日动量：过去20个交易日累计收益率",
    params={"period": 20},
    required_data=["close"],
    lookback_days=20,
)
def momentum_20d(data, date: str, period: int = 20):
    """20日收益率动量：(今收 - N日前收) / N日前收"""
    dates = data.get_trade_calendar()
    if date not in dates:
        return pd.Series(dtype=float)
    idx = dates.index(date)
    if idx < period:
        return pd.Series(dtype=float)
    past_date = dates[idx - period]
    close_now = data.get_close_price(date)
    close_past = data.get_close_price(past_date)
    combined = pd.concat([close_now.rename("now"), close_past.rename("past")], axis=1).dropna()
    if combined.empty:
        return pd.Series(dtype=float)
    return (combined["now"] / combined["past"] - 1).clip(-0.5, 0.5)


@FactorRegistry.register(
    name="momentum_60d",
    category="momentum",
    description="60日动量",
    params={"period": 60},
    required_data=["close"],
    lookback_days=60,
)
def momentum_60d(data, date: str, period: int = 60):
    dates = data.get_trade_calendar()
    if date not in dates:
        return pd.Series(dtype=float)
    idx = dates.index(date)
    if idx < period:
        return pd.Series(dtype=float)
    past_date = dates[idx - period]
    close_now = data.get_close_price(date)
    close_past = data.get_close_price(past_date)
    combined = pd.concat([close_now.rename("now"), close_past.rename("past")], axis=1).dropna()
    if combined.empty:
        return pd.Series(dtype=float)
    return (combined["now"] / combined["past"] - 1).clip(-1.0, 1.0)


@FactorRegistry.register(
    name="vol_adj_momentum_20d",
    category="momentum",
    description="波动率调整动量：20日收益 / 20日波动率",
    params={"period": 20},
    required_data=["close"],
    lookback_days=20,
)
def vol_adj_momentum(data, date: str, period: int = 20):
    """波动率调整动量 — 用原始动量除以波动率"""
    raw_mom = momentum_20d(data, date, period)
    if raw_mom.empty:
        return pd.Series(dtype=float)
    # 跨类别引用：波动率因子取负号，这里还原为正值
    from .volatility import volatility_20d as vol_func
    vol = vol_func(data, date, period)
    real_vol = -vol  # 还原为正值波动率
    result = raw_mom / real_vol.replace(0, np.nan)
    return result.clip(-5, 5)
