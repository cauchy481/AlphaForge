"""缺失值填充"""
import pandas as pd


class MissingFiller:

    def __init__(self, method: str = "industry_median"):
        """
        method: "industry_median" / "median" / "zero" / "drop"
        """
        self.method = method

    def process(
        self,
        series: pd.Series,
        industry_series: pd.Series = None,
    ) -> pd.Series:
        """填充单个因子的缺失值"""
        if self.method == "zero":
            return series.fillna(0.0)
        if self.method == "median":
            return series.fillna(series.median())
        if self.method == "industry_median" and industry_series is not None:
            # 对齐索引
            common_idx = series.dropna().index.intersection(industry_series.dropna().index)
            if len(common_idx) == 0:
                return series.fillna(series.median())
            aligned = pd.DataFrame({
                "value": series.reindex(common_idx),
                "industry": industry_series.reindex(common_idx),
            })
            group_median = aligned.groupby("industry")["value"].transform("median")
            filled = aligned["value"].fillna(group_median)
            # 某行业全部 NaN → 全市场中位数
            result = series.copy()
            result.loc[filled.index] = filled
            return result.fillna(result.median())
        if self.method == "drop":
            return series.dropna()
        return series.fillna(series.median())
