"""反转类因子"""
import pandas as pd
from .registry import FactorRegistry
from .momentum import momentum_20d  # 复用动量计算逻辑


@FactorRegistry.register(
    name="reversal_5d",
    category="reversal",
    description="5日反转：过去5日跌幅最大的股票（取负号后值越大预期反弹越强）",
    params={"period": 5},
    required_data=["close"],
    lookback_days=5,
)
def reversal_5d(data, date: str, period: int = 5):
    """短期反转 — 买入近期超跌的股票"""
    mom = momentum_20d(data, date, period)
    if mom.empty:
        return pd.Series(dtype=float)
    return -mom.clip(-0.5, 0.5)


@FactorRegistry.register(
    name="reversal_10d",
    category="reversal",
    description="10日反转",
    params={"period": 10},
    required_data=["close"],
    lookback_days=10,
)
def reversal_10d(data, date: str, period: int = 10):
    mom = momentum_20d(data, date, period)
    if mom.empty:
        return pd.Series(dtype=float)
    return -mom.clip(-0.5, 0.5)
