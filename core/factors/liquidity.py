"""流动性类因子"""
import numpy as np
import pandas as pd
from .registry import FactorRegistry


@FactorRegistry.register(
    name="turnover_20d",
    category="liquidity",
    description="20日平均换手率（取负号，低换手因子值高）",
    params={"period": 20},
    required_data=["volume"],
    lookback_days=20,
)
def turnover_20d(data, date: str, period: int = 20):
    """换手率因子 — 低换手率股票因子值高"""
    vol = data.get_volume(date)
    if vol.empty:
        return pd.Series(dtype=float)
    # 用成交量变化近似换手率
    turnover = vol.pct_change().rolling(period).mean()
    return -turnover.clip(-0.2, 0.2)


@FactorRegistry.register(
    name="amount_20d",
    category="liquidity",
    description="20日平均成交额（取负号，低成交额因子值高）",
    params={"period": 20},
    required_data=["amount"],
    lookback_days=20,
)
def amount_20d(data, date: str, period: int = 20):
    """成交额因子"""
    amt = data.get_amount(date)
    if amt.empty:
        return pd.Series(dtype=float)
    avg_amt = amt.rolling(period).mean()
    log_amt = np.log(avg_amt.replace(0, np.nan))
    return -log_amt  # 取负：小盘股因子值高
