"""Williams %R 因子"""
import numpy as np
import pandas as pd
from .registry import FactorRegistry


@FactorRegistry.register(
    name="williams_r_20d",
    category="technical",
    description="Williams %R — (HH_20 - Close) / (HH_20 - LL_20), 捕捉短期超卖反弹",
    params={"period": 20},
    required_data=["close", "high", "low"],
    lookback_days=20,
)
def williams_r_20d(data, date: str, period: int = 20):
    """WR = (HH_n - Close) / (HH_n - LL_n)"""
    dates = data.get_trade_calendar()
    if date not in dates:
        return pd.Series(dtype=float)
    idx = dates.index(date)
    if idx < period:
        return pd.Series(dtype=float)

    lookback_dates = dates[idx - period: idx + 1]
    frames = []
    for d in lookback_dates:
        df = data.get_daily_data(d)
        if df.empty:
            return pd.Series(dtype=float)
        if "code" not in df.columns and "ts_code" in df.columns:
            df["code"] = df["ts_code"]
        df = df.set_index("code")
        frames.append(df[["high", "low", "close"]].astype(float))

    high_df = pd.concat([f["high"] for f in frames], axis=1)
    low_df = pd.concat([f["low"] for f in frames], axis=1)
    close_now = frames[-1]["close"]

    hh = high_df.max(axis=1)
    ll = low_df.min(axis=1)
    spread = hh - ll

    wr = (hh - close_now) / spread.replace(0, np.nan)
    return wr.clip(0, 1)
