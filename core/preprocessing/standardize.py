"""标准化"""
import pandas as pd


class Standardizer:
    def __init__(self, method: str = "zscore"):
        """
        method: "zscore" / "rank" / "minmax" / "robust"
        """
        self.method = method

    def process(self, series: pd.Series) -> pd.Series:
        if self.method == "zscore":
            std = series.std()
            if std == 0 or pd.isna(std):
                return series * 0.0
            return (series - series.mean()) / std
        if self.method == "rank":
            return series.rank(pct=True)
        if self.method == "minmax":
            lo, hi = series.min(), series.max()
            if hi == lo:
                return series * 0.0
            return (series - lo) / (hi - lo)
        if self.method == "robust":
            median = series.median()
            mad = (series - median).abs().median()
            if mad == 0 or pd.isna(mad):
                return series - median
            return (series - median) / mad
        return series
