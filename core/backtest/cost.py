"""交易成本模型"""
class CostModel:
    def __init__(
        self,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.001,
        stamp_duty: float = 0.001,
    ):
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.stamp_duty = stamp_duty

    def buy_cost_rate(self) -> float:
        """买入成本率 = 佣金 + 滑点"""
        return self.commission_rate + self.slippage_rate

    def sell_cost_rate(self) -> float:
        """卖出成本率 = 佣金 + 滑点 + 印花税"""
        return self.commission_rate + self.slippage_rate + self.stamp_duty

    def roundtrip_cost_rate(self) -> float:
        """一次完整买卖的成本率"""
        return self.buy_cost_rate() + self.sell_cost_rate()

    def estimate_impact(
        self,
        amount: float,
        daily_volume: float,
        participation_rate: float = 0.05,
    ) -> float:
        """
        估算市场冲击成本
        amount: 交易金额
        daily_volume: 日均成交额
        participation_rate: 参与率上限
        """
        if daily_volume <= 0:
            return self.slippage_rate
        participation = amount / daily_volume
        if participation <= participation_rate:
            return self.slippage_rate
        # 超线性惩罚
        return self.slippage_rate * (participation / participation_rate) ** 0.5
