"""事件驱动回测引擎"""
import numpy as np
import pandas as pd
from typing import List, Optional

from .portfolio import PortfolioManager
from .performance import PerformanceEvaluator


class BacktestEngine:
    def __init__(
        self,
        data_loader,
        initial_capital: float = 1_000_000.0,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.001,
        stamp_duty: float = 0.001,
        risk_free_rate: float = 0.03,
    ):
        self.loader = data_loader
        self.portfolio = PortfolioManager(
            initial_capital, commission_rate, slippage_rate, stamp_duty
        )
        self.evaluator = PerformanceEvaluator(risk_free_rate)

    def run(
        self,
        start_date: str,
        end_date: str,
        factor_name: str = "momentum_20d",
        factor_values: Optional[dict] = None,
        top_n: int = 50,
        rebalance_freq: int = 5,
        enable_cost: bool = True,
        calculate_ic: bool = True,
    ) -> dict:

        trade_dates = self.loader.get_trade_calendar(start_date, end_date)
        use_external = factor_values is not None

        daily_returns_list = []
        daily_returns_dates = []
        ic_list = []
        ic_dates = []
        turnover_list = []

        for i, dt in enumerate(trade_dates):
            # 第一天跳过
            prev_dt = trade_dates[i - 1] if i > 0 else None

            # ── 盘前：用 T-1 数据生成信号 ──
            signal = []
            if prev_dt is not None:
                if use_external:
                    signal = self._signal_from_series(prev_dt, factor_values, top_n)
                else:
                    signal = self._generate_signal(prev_dt, factor_name, top_n)

            # ── 盘中：调仓 ──
            is_rebalance = (i % rebalance_freq == 0)
            rebalance_info = None
            if is_rebalance and signal:
                rebalance_info = self.portfolio.rebalance(signal)
                turnover_list.append(rebalance_info["turnover"])
                if i < 5 * rebalance_freq:
                    label = factor_name if not use_external else "composite"
                    print(f"{dt} | 选股({label}): {signal[:3]}... | 换手: {rebalance_info['turnover']:.1%}")

            # ── 盘后：收益结算 ──
            ret_df = self.loader.get_daily_data(dt)
            if ret_df.empty:
                continue
            if "code" not in ret_df.columns and "ts_code" in ret_df.columns:
                ret_df["code"] = ret_df["ts_code"]
            ret_df = ret_df.set_index("code")

            port_ret = self._calc_portfolio_return(
                ret_df, enable_cost, rebalance_info
            )
            if port_ret is not None:
                daily_returns_list.append(port_ret)
                daily_returns_dates.append(dt)
                self.portfolio.update_capital(port_ret)

            if calculate_ic and prev_dt is not None:
                if use_external:
                    ic = self._calc_ic_from_series(prev_dt, ret_df, factor_values)
                else:
                    ic = self._calc_daily_ic(prev_dt, ret_df, factor_name)
                if not np.isnan(ic):
                    ic_list.append(ic)
                    ic_dates.append(dt)

        returns_series = pd.Series(daily_returns_list, index=daily_returns_dates, dtype=float)
        cumulative = (1 + returns_series).cumprod()

        report = self.evaluator.generate_report(cumulative, returns_series)

        if calculate_ic and ic_list:
            ic_series = pd.Series(ic_list, index=ic_dates)
            ic_stats = self.evaluator.calculate_ic_ir(ic_series)
            report.update(ic_stats)

        trade_stats = self.portfolio.get_statistics()
        report["total_cost"] = trade_stats["total_cost"]
        report["trade_count"] = trade_stats["trade_count"]
        report["avg_turnover"] = np.mean(turnover_list) if turnover_list else 0
        report["ic_series"] = pd.Series(ic_list, index=ic_dates) if ic_list else None

        return report

    def _generate_signal(self, date: str, factor_name: str, top_n: int) -> List[str]:
        """用指定日期的收盘数据计算因子值，排序，取 Top N"""
        from ..factors.registry import FactorRegistry

        factor_info = FactorRegistry.get(factor_name)
        if factor_info is None:
            return []

        factor_series = FactorRegistry.compute(factor_name, self.loader, date)
        if factor_series.empty:
            return []

        return factor_series.dropna().nlargest(top_n).index.tolist()

    def _signal_from_series(
        self, date: str, factor_values: dict, top_n: int
    ) -> List[str]:
        """从预计算的因子值字典中取信号，支持多因子合成后传入"""
        series = factor_values.get(date)
        if series is None or series.empty:
            return []
        return series.dropna().nlargest(top_n).index.tolist()

    def _calc_portfolio_return(
        self,
        ret_df: pd.DataFrame,
        enable_cost: bool,
        rebalance_info: Optional[dict] = None,
    ) -> Optional[float]:
        """计算组合当日等权益率"""
        holdings = self.portfolio.current_holdings
        if not holdings:
            return None

        # 当日涨跌幅 pct_chg
        if "pct_chg" in ret_df.columns:
            ret_col = "pct_chg"
        elif "1vwap_pct" in ret_df.columns:
            ret_col = "1vwap_pct"
        else:
            return None

        holdings_ret = ret_df[ret_df.index.isin(holdings)]
        if holdings_ret.empty:
            return None

        port_ret = holdings_ret[ret_col].astype(float).mean() / 100.0  

        # 扣除调仓成本
        if enable_cost and rebalance_info is not None:
            cost_rate = rebalance_info["total_cost"] / self.portfolio.current_capital
            port_ret -= cost_rate

        return float(port_ret)

    def _calc_daily_ic(
        self,
        factor_date: str,
        ret_df: pd.DataFrame,
        factor_name: str,
    ) -> float:
        """IC = Corr(Factor_{factor_date}, Return from ret_df) """
        from ..factors.registry import FactorRegistry

        factor_series = FactorRegistry.compute(factor_name, self.loader, factor_date)
        if factor_series.empty:
            return np.nan

        ret_series = self._extract_ret_series(ret_df)
        if ret_series is None:
            return np.nan

        ic = self.evaluator.calculate_ic(factor_series, ret_series)
        return ic

    def _calc_ic_from_series(
        self, factor_date: str, ret_df: pd.DataFrame, factor_values: dict
    ) -> float:
        """用预计算因子值算 IC"""
        factor_series = factor_values.get(factor_date)
        if factor_series is None or factor_series.empty:
            return np.nan

        ret_series = self._extract_ret_series(ret_df)
        if ret_series is None:
            return np.nan

        return self.evaluator.calculate_ic(factor_series, ret_series)

    def _extract_ret_series(self, ret_df: pd.DataFrame):
        """从日线 DataFrame 提取收益率 Series"""
        if "pct_chg" in ret_df.columns:
            return ret_df["pct_chg"].astype(float) / 100.0
        elif "1vwap_pct" in ret_df.columns:
            return ret_df["1vwap_pct"].astype(float)
        return None

    def print_report(self, report: dict) -> None:

        print("回测绩效报告：")
        print(f"总收益率:       {report['total_return']*100:>10.2f}%")
        print(f"年化收益率:     {report['annual_return']*100:>10.2f}%")
        print(f"年化波动率:     {report['annual_volatility']*100:>10.2f}%")
        print(f"夏普比率:       {report['sharpe_ratio']:>10.2f}")
        print(f"最大回撤:       {report['max_drawdown']*100:>10.2f}%")
        print(f"卡玛比率:       {report['calmar_ratio']:>10.2f}")
        print(f"胜率:           {report['win_rate']*100:>10.2f}%")

        if report.get("ic_mean") is not None:
            print(f"\nIC 均值:        {report['ic_mean']:>10.4f}")
            print(f"IC IR:          {report.get('ir', 0):>10.4f}")
            print(f"IC 胜率:        {report.get('ic_win_rate', 0)*100:>10.2f}%")

        print(f"\n总交易成本:     {report['total_cost']:>10.0f} 元")
        print(f"平均换手率:     {report['avg_turnover']*100:>10.2f}%")
