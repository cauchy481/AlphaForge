"""价值类因子"""
import numpy as np
import pandas as pd
from .registry import FactorRegistry


@FactorRegistry.register(
    name="ep_ttm",
    category="value",
    description="EP (TTM)：净利润TTM / 总市值",
    params={},
    required_data=["close"],
    lookback_days=0,
)
def ep_ttm(data, date: str):
    """盈利市值比"""
    df = data.get_daily_data(date)
    if df.empty:
        return pd.Series(dtype=float)
    if "code" not in df.columns and "ts_code" in df.columns:
        df["code"] = df["ts_code"]
    df = df.set_index("code")
    # EP = 1 / PE_ttm（仅当 PE > 0）
    if "pe_ttm" in df.columns:
        pe = df["pe_ttm"].astype(float)
        ep = (1.0 / pe).replace([np.inf, -np.inf], np.nan)
        ep[pe <= 0] = np.nan
        return ep.clip(0, 0.5)
    return pd.Series(dtype=float)


@FactorRegistry.register(
    name="pb_inverse",
    category="value",
    description="BP (市净率倒数)：1 / PB",
    params={},
    required_data=["close"],
    lookback_days=0,
)
def pb_inverse(data, date: str):
    """净资产市值比"""
    df = data.get_daily_data(date)
    if df.empty:
        return pd.Series(dtype=float)
    if "code" not in df.columns and "ts_code" in df.columns:
        df["code"] = df["ts_code"]
    df = df.set_index("code")
    if "pb" in df.columns:
        pb = df["pb"].astype(float)
        bp = (1.0 / pb).replace([np.inf, -np.inf], np.nan)
        bp[pb <= 0] = np.nan
        return bp.clip(0, 10)
    return pd.Series(dtype=float)
