"""回测结果分析"""
import numpy as np
import pandas as pd


class PerformanceEvaluator:
    """计算回测绩效指标"""

    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = risk_free_rate

    def generate_report(
        self,
        cumulative_returns: pd.Series,
        daily_returns: pd.Series,
    ) -> dict:
        """完整绩效报告"""
        if daily_returns.empty:
            return self._empty_report()

        total_ret = float(cumulative_returns.iloc[-1] - 1)
        ann_ret = self._annual_return(daily_returns)
        ann_vol = self._annual_volatility(daily_returns)
        sharpe = (ann_ret - self.risk_free_rate) / ann_vol if ann_vol > 0 else 0
        mdd = self._max_drawdown(daily_returns)
        calmar = ann_ret / abs(mdd) if mdd != 0 else 0
        win = float((daily_returns > 0).mean())

        return {
            "total_return": total_ret,
            "annual_return": ann_ret,
            "annual_volatility": ann_vol,
            "sharpe_ratio": sharpe,
            "max_drawdown": mdd,
            "calmar_ratio": calmar,
            "win_rate": win,
            "cumulative_returns": cumulative_returns,
            "daily_returns": daily_returns,
        }

    def _annual_return(self, returns: pd.Series) -> float:
        total = (1 + returns).prod()
        return float(total ** (252 / max(len(returns), 1)) - 1)

    def _annual_volatility(self, returns: pd.Series) -> float:
        return float(returns.std() * np.sqrt(252))

    def _max_drawdown(self, returns: pd.Series) -> float:
        cumulative = (1 + returns).cumprod()
        peak = cumulative.cummax()
        drawdown = cumulative / peak - 1
        return float(drawdown.min())

    def calculate_ic(self, factor: pd.Series, forward_return: pd.Series) -> float:
        """截面 Rank IC"""
        aligned = pd.concat([factor, forward_return], axis=1).dropna()
        if len(aligned) < 30:
            return np.nan
        return aligned.iloc[:, 0].corr(aligned.iloc[:, 1], method="spearman")

    def calculate_ic_ir(self, ic_series: pd.Series) -> dict:
        """IC 序列统计"""
        clean = ic_series.dropna()
        if clean.empty:
            return {"ic_mean": np.nan, "ic_std": np.nan, "ir": np.nan, "ic_win_rate": np.nan}

        mean = clean.mean()
        std = clean.std(ddof=1)
        ir = mean / std if std > 1e-12 else np.nan
        win_rate = (clean > 0).mean()
        return {"ic_mean": mean, "ic_std": std, "ir": ir, "ic_win_rate": win_rate}

    def _empty_report(self) -> dict:
        return {
            "total_return": 0, "annual_return": 0, "annual_volatility": 0,
            "sharpe_ratio": 0, "max_drawdown": 0, "calmar_ratio": 0,
            "win_rate": 0, "cumulative_returns": pd.Series(), "daily_returns": pd.Series(),
        }
