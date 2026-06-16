"""去极值处理"""
import pandas as pd
import numpy as np


class OutlierHandler:

    def __init__(self, method: str = "mad", n: float = 5.0):
        """
        method: "mad" / "sigma" / "percentile"
        """
        self.method = method
        self.n = n

    def _winsor_mad(self, series: pd.Series) -> pd.Series:
        """MAD 法: median ± n * 1.4826 * MAD"""
        median = series.median()
        mad = (series - median).abs().median()
        if pd.isna(mad) or mad == 0:
            return series
        upper = median + self.n * 1.4826 * mad
        lower = median - self.n * 1.4826 * mad
        return series.clip(lower, upper)

    def _winsor_sigma(self, series: pd.Series) -> pd.Series:
        """Sigma 法: mean ± n * std"""
        mean = series.mean()
        std = series.std()
        if pd.isna(std) or std == 0:
            return series
        upper = mean + self.n * std
        lower = mean - self.n * std
        return series.clip(lower, upper)

    def _winsor_percentile(self, series: pd.Series) -> pd.Series:
        """百分位法: 默认 n=5 表示 2.5% / 97.5%"""
        lower_pct = self.n / 2
        upper_pct = 100 - self.n / 2
        lower = series.quantile(lower_pct / 100)
        upper = series.quantile(upper_pct / 100)
        return series.clip(lower, upper)

    def process(self, series: pd.Series) -> pd.Series:
        series = series.replace([np.inf, -np.inf], np.nan)
        if self.method == "mad":
            return self._winsor_mad(series)
        elif self.method == "sigma":
            return self._winsor_sigma(series)
        elif self.method == "percentile":
            return self._winsor_percentile(series)
        return series
