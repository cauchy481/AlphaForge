"""因子中性化"""
import numpy as np
import pandas as pd
import statsmodels.api as sm


class Neutralizer:
    def __init__(
        self,
        method: str = "industry_size",
        size_col: str = "size",
    ):
        self.method = method
        self.size_col = size_col

    def _build_design_matrix(
        self,
        df: pd.DataFrame,
        industry_series: pd.Series = None,
    ) -> pd.DataFrame:
        """构建设计矩阵 X"""
        X = pd.DataFrame(index=df.index)

        if self.method in ("size", "industry_size", "barra"):
            for col_candidate in [self.size_col, "mktcap", "total_mv", "circ_mv"]:
                if col_candidate in df.columns:
                    raw = df[col_candidate].astype(float)
                    X["size"] = np.log(raw.replace(0, np.nan))
                    break

        if self.method in ("industry", "industry_size", "barra") and industry_series is not None:
            # 行业哑变量, 含截距项时 drop_first 避免共线性
            dummies = pd.get_dummies(industry_series, prefix="ind", drop_first=True)
            dummies.index = df.index
            X = pd.concat([X, dummies], axis=1)

        X = X.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
        X = sm.add_constant(X, has_constant="add")
        return X

    def neutralize(
        self,
        factor_series: pd.Series,
        barra_df: pd.DataFrame = None,
        industry_series: pd.Series = None,
    ) -> pd.Series:
        """单因子中性化"""
        if self.method == "none":
            return factor_series

        df = pd.DataFrame({"factor": factor_series})
        if barra_df is not None:
            df = pd.concat([df, barra_df], axis=1)

        X = self._build_design_matrix(df, industry_series)

        aligned = pd.concat([factor_series.rename("y"), X], axis=1).dropna()
        if aligned.empty or aligned.shape[0] <= X.shape[1] + 1:
            return factor_series  # 样本不足，跳过中性化

        y = aligned["y"]
        x = aligned[X.columns]

        try:
            model = sm.OLS(y, x).fit()
            resid = pd.Series(model.resid, index=aligned.index)
            # 填回原始索引
            result = factor_series.copy()
            result.loc[resid.index] = resid
            return result
        except Exception:
            return factor_series
