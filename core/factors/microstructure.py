"""微观结构类因子

Amihud (2002) 非流动性因子：|r_t| / Amount_t，低流动性溢价的度量。
MAX 因子：过去 N 日最大单日涨幅，彩票效应因子。

两者在 A 股市场均有大量实证支持。
"""
import numpy as np
import pandas as pd
from .registry import FactorRegistry


def _load_pct_amount_panel(data, date: str, period: int):
    """读取 [date-period, date) 的 pct_chg / amount 面板，返回 (pct_panel, amt_panel)"""
    dates = data.get_trade_calendar()
    if date not in dates:
        return None, None
    idx = dates.index(date)
    if idx < period:
        return None, None
    lookback_dates = dates[idx - period: idx]

    pct_list, amt_list = [], []
    for dt in lookback_dates:
        df = data.get_daily_data(dt)
        if df.empty:
            continue
        if "code" not in df.columns and "ts_code" in df.columns:
            df = df.rename(columns={"ts_code": "code"})
        df = df.set_index("code")
        if "pct_chg" in df.columns:
            pct_list.append(df["pct_chg"].astype(float).rename(dt))
        if "amount" in df.columns:
            amt_list.append(df["amount"].astype(float).rename(dt))

    pct_panel = pd.concat(pct_list, axis=1) if pct_list else pd.DataFrame()
    amt_panel = pd.concat(amt_list, axis=1) if amt_list else pd.DataFrame()
    return pct_panel, amt_panel


@FactorRegistry.register(
    name="amihud_illiq_20d",
    category="microstructure",
    description=(
        "Amihud 非流动性因子(20日)：mean(|pct_chg/100| / amount_元) × 10^8。"
        "高值=流动性差=预期收益高，正向使用。"
    ),
    params={"period": 20},
    required_data=["pct_chg", "amount"],
    lookback_days=20,
)
def amihud_illiq_20d(data, date: str, period: int = 20) -> pd.Series:
    """Amihud(2002) 非流动性：过去 period 日 |日收益率| / 日成交额 的均值。"""
    pct_panel, amt_panel = _load_pct_amount_panel(data, date, period)
    if pct_panel is None or pct_panel.empty or amt_panel.empty:
        return pd.Series(dtype=float)

    # pct_chg 单位 %，amount 单位 千元 → 转元
    ret_abs = pct_panel.abs() / 100.0
    amt_yuan = amt_panel * 1000.0
    illiq = ret_abs / amt_yuan.replace(0, np.nan)

    mean_illiq = illiq.mean(axis=1)
    # ×10^8 使典型值落在 0.01-50 区间
    return (mean_illiq * 1e8).clip(0, 500)


@FactorRegistry.register(
    name="max_ret_20d",
    category="microstructure",
    description=(
        "MAX 彩票因子(20日)：过去 20 日最大单日涨幅取负号。"
        "彩票效应下高 MAX 股票被高估，取负后高因子值=低彩票性=预期收益高。"
    ),
    params={"period": 20},
    required_data=["pct_chg"],
    lookback_days=20,
)
def max_ret_20d(data, date: str, period: int = 20) -> pd.Series:
    """MAX 因子：取负号使其与未来收益正相关（彩票股倾向于underperform）。"""
    pct_panel, _ = _load_pct_amount_panel(data, date, period)
    if pct_panel is None or pct_panel.empty:
        return pd.Series(dtype=float)

    max_ret = (pct_panel / 100.0).max(axis=1)
    return -max_ret.clip(-0.15, 0.15)
