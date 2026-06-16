"""预处理管线"""
import pandas as pd
from typing import Optional, List

from .universe import UniverseFilter
from .outliers import OutlierHandler
from .missing import MissingFiller
from .standardize import Standardizer
from .neutralizer import Neutralizer


class PreprocessingPipeline:
    """因子预处理管线：股票池过滤 → 去极值 → 缺失值填充 → 标准化 → 中性化"""

    def __init__(
        self,
        winsorize_method: str = "mad",
        winsorize_n: float = 5.0,
        fill_method: str = "industry_median",
        standardize_method: str = "zscore",
        neutralize_method: str = "industry_size",
        min_list_days: int = 60,
        min_daily_amount: float = 5_000_000,
        exclude_st: bool = True,
    ):
        self.universe = UniverseFilter(min_list_days, min_daily_amount, exclude_st)
        self.outliers = OutlierHandler(winsorize_method, winsorize_n)
        self.filler = MissingFiller(fill_method)
        self.standardizer = Standardizer(standardize_method)
        self.neutralizer = Neutralizer(neutralize_method)

    def run(
        self,
        df: pd.DataFrame,
        factor_cols: Optional[List[str]] = None,
        date: str = None,
        industry_series: pd.Series = None,
        stock_list: pd.DataFrame = None,
        barra_df: pd.DataFrame = None,
    ) -> pd.DataFrame:
        """
        df: 包含 code 和因子列的 DataFrame
        factor_cols: 需要处理的因子列名列表，不指定则自动推断
        """
        if df.empty:
            return df

        # 自动推断因子列（排除非因子列）
        skip = {"code", "date", "name", "industry", "ts_code", "list_date"}
        if factor_cols is None:
            factor_cols = [c for c in df.columns if c not in skip]

        # 确保 code 列存在
        if "code" not in df.columns and "ts_code" in df.columns:
            df = df.rename(columns={"ts_code": "code"})

        # 股票池过滤
        df = self.universe.filter(df, date=date, stock_list=stock_list)

        # 逐因子清洗
        result = df.copy()
        for col in factor_cols:
            if col not in result.columns:
                continue
            series = result[col].astype(float)
            series = self.outliers.process(series)      # 去极值
            series = self.filler.process(series, industry_series)  # 填充缺失
            series = self.standardizer.process(series)   # 标准化
            result[col] = series

        #中性化:逐因子回归取残差
        if self.neutralizer.method != "none":
            for col in factor_cols:
                if col in result.columns:
                    result[col] = self.neutralizer.neutralize(
                        result[col],
                        barra_df=barra_df,
                        industry_series=industry_series,
                    )

        return result

    def run_factor_series(
        self,
        factor_series: pd.Series,
        industry_series: pd.Series = None,
        barra_df: pd.DataFrame = None,
    ) -> pd.Series:
        """对单个因子 Series 执行完整预处理"""
        series = factor_series.astype(float).replace([float('inf'), float('-inf')], float('nan'))
        series = self.outliers.process(series)
        series = self.filler.process(series, industry_series)
        series = self.standardizer.process(series)
        if self.neutralizer.method != "none":
            series = self.neutralizer.neutralize(series, barra_df, industry_series)
        return series
