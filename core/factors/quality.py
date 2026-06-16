"""质量类因子"""
import pandas as pd
from .registry import FactorRegistry


@FactorRegistry.register(
    name="roe",
    category="quality",
    description="ROE：净资产收益率",
    params={},
    required_data=[],
    lookback_days=0,
)
def roe(data, date: str):
    """ROE"""
    df = data.get_daily_data(date)
    if df.empty:
        return pd.Series(dtype=float)
    if "code" not in df.columns and "ts_code" in df.columns:
        df["code"] = df["ts_code"]
    df = df.set_index("code")
    if "roe" in df.columns:
        return df["roe"].astype(float).clip(-0.5, 0.5)
    return pd.Series(dtype=float)
