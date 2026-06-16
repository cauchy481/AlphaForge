"""波动率类因子"""
import pandas as pd
from .registry import FactorRegistry


@FactorRegistry.register(
    name="volatility_20d",
    category="volatility",
    description="20日波动率（取负号，低波动因子的值更高）",
    params={"period": 20},
    required_data=["close"],
    lookback_days=20,
)
def volatility_20d(data, date: str, period: int = 20):
    """历史波动率"""
    dates = data.get_trade_calendar()
    if date not in dates:
        return pd.Series(dtype=float)
    idx = dates.index(date)
    if idx < period:
        return pd.Series(dtype=float)
    lookback_dates = dates[idx - period: idx + 1]
    close_df = pd.DataFrame({d: data.get_close_price(d) for d in lookback_dates})
    returns = close_df.pct_change().dropna(how="all")
    vol = returns.std()
    return -vol.clip(0, 0.1)


@FactorRegistry.register(
    name="volatility_60d",
    category="volatility",
    description="60日波动率（取负号）",
    params={"period": 60},
    required_data=["close"],
    lookback_days=60,
)
def volatility_60d(data, date: str, period: int = 60):
    dates = data.get_trade_calendar()
    if date not in dates:
        return pd.Series(dtype=float)
    idx = dates.index(date)
    if idx < period:
        return pd.Series(dtype=float)
    lookback_dates = dates[idx - period: idx + 1]
    close_df = pd.DataFrame({d: data.get_close_price(d) for d in lookback_dates})
    returns = close_df.pct_change().dropna(how="all")
    vol = returns.std()
    return -vol.clip(0, 0.1)
