"""交易日历与通用工具"""
import pickle
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

from .metrics import (
    max_drawdown,
    annual_return,
    annual_volatility,
    sharpe_ratio,
    calmar_ratio,
    win_rate,
    information_ratio,
    rolling_sharpe,
)


def load_trade_calendar(path: str = None) -> List[str]:
    """加载交易日历 pickle 文件，返回排序后的日期字符串列表"""
    if path is None:
        path = Path(__file__).parent.parent.parent / "data_cache" / "calendar.pkl"
    with open(path, "rb") as f:
        dates = pickle.load(f)
    return sorted(dates)


def filter_dates(
    dates: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[str]:
    """按起止日期过滤交易日列表"""
    if start_date:
        dates = [d for d in dates if d >= start_date]
    if end_date:
        dates = [d for d in dates if d <= end_date]
    return dates


def window_dates(dates: List[str], window: int):
    """生成滚动窗口生成器：每次 yield 当前日期之前 window 天的日期列表（不含当日）"""
    for idx in range(len(dates)):
        start = max(0, idx - window)
        yield dates[start:idx]


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def series_to_frame(series: pd.Series, col_name: str = "factor_value") -> pd.DataFrame:
    """将 Series 转为标准因子 DataFrame 格式（code 为列，含 date 列）"""
    df = series.reset_index()
    df.columns = ["code", col_name]
    return df
