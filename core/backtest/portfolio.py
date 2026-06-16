"""资金、持仓、交易成本"""
from typing import List


class PortfolioManager:
    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.001,
        stamp_duty: float = 0.001,
    ):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_rate = commission_rate   # 佣金（买卖）
        self.slippage_rate = slippage_rate         # 滑点
        self.stamp_duty = stamp_duty               # 印花税（卖出）

        self.current_holdings: List[str] = []
        self.total_cost = 0.0
        self.trade_count = 0

    def rebalance(self, target_holdings: List[str]) -> dict:
        """
        调仓：根据目标持仓计算买入/卖出清单，估算交易成本
        返回 dict 含 turnover, total_cost, buy_list, sell_list
        """
        current = set(self.current_holdings)
        target = set(target_holdings)

        to_buy = list(target - current)
        to_sell = list(current - target)

        n_stocks = max(len(self.current_holdings), len(target_holdings), 1)
        # 换手率
        turnover = (len(to_buy) + len(to_sell)) / (2 * n_stocks)

        # 估算交易成本
        weight_per_stock = 1.0 / n_stocks
        buy_cost = len(to_buy) * weight_per_stock * (self.commission_rate + self.slippage_rate)
        sell_cost = len(to_sell) * weight_per_stock * (self.commission_rate + self.slippage_rate + self.stamp_duty)
        total_cost = self.current_capital * (buy_cost + sell_cost)

        self.current_holdings = target_holdings
        self.total_cost += total_cost
        self.trade_count += len(to_buy) + len(to_sell)

        return {
            "turnover": turnover,
            "total_cost": total_cost,
            "buy_list": to_buy,
            "sell_list": to_sell,
        }

    def update_capital(self, daily_return: float) -> None:
        """根据日收益率更新资金"""
        self.current_capital *= (1 + daily_return)

    def get_statistics(self) -> dict:
        return {
            "total_cost": self.total_cost,
            "trade_count": self.trade_count,
            "final_capital": self.current_capital,
        }
