"""技术类因子"""
import numpy as np
import pandas as pd
from .registry import FactorRegistry


@FactorRegistry.register(
    name="rsi_14d",
    category="technical",
    description="14日RSI指标",
    params={"period": 14},
    required_data=["close"],
    lookback_days=14,
)
def rsi_14d(data, date: str, period: int = 14):
    """相对强弱指标 RSI"""
    dates = data.get_trade_calendar()
    if date not in dates:
        return pd.Series(dtype=float)
    idx = dates.index(date)
    if idx < period + 1:
        return pd.Series(dtype=float)
    lookback_dates = dates[idx - period - 1: idx + 1]
    close_df = pd.DataFrame({d: data.get_close_price(d) for d in lookback_dates})
    delta = close_df.diff().dropna(how="all")
    gain = delta.clip(lower=0).mean()
    loss = (-delta).clip(lower=0).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return (rsi - 50) / 50


@FactorRegistry.register(
    name="bias_20d",
    category="technical",
    description="20日乖离率：(收盘价 - 20日均价) / 20日均价",
    params={"period": 20},
    required_data=["close"],
    lookback_days=20,
)
def bias_20d(data, date: str, period: int = 20):
    """乖离率"""
    dates = data.get_trade_calendar()
    if date not in dates:
        return pd.Series(dtype=float)
    idx = dates.index(date)
    if idx < period:
        return pd.Series(dtype=float)
    lookback_dates = dates[idx - period: idx + 1]
    close_df = pd.DataFrame({d: data.get_close_price(d) for d in lookback_dates})
    ma = close_df.mean()
    current = close_df.iloc[-1]
    bias = (current - ma) / ma.replace(0, np.nan)
    return bias.clip(-0.3, 0.3)
