"""回测运行入口"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import load_config
from core.data import DataLoader
from core.backtest import BacktestEngine


def main():
    cfg = load_config()
    token = cfg["tushare"]["token"]
    if not token or token == "YOUR_TUSHARE_TOKEN_HERE":
        print("请先在 config/settings.yaml 中填入 Tushare Token")
        return

    loader = DataLoader(
        token=token,
        cache_dir=cfg["data"]["cache_dir"],
    )

    start = "20240101"
    end = "20241231"

    print("下载日线行情数据...")
    loader.download_daily_batch(start, end)

    print("下载每日基本面指标（PE/PB/市值）...")
    loader.download_daily_basic(start, end)

    print("下载基准指数日线（沪深300、中证500）...")
    loader.download_index_daily(
        index_codes=["000300.SH", "000905.SH"],
        start_date=start,
        end_date=end,
    )

    engine = BacktestEngine(
        data_loader=loader,
        initial_capital=cfg["backtest"]["initial_capital"],
        commission_rate=cfg["backtest"]["commission_rate"],
        slippage_rate=cfg["backtest"]["slippage_rate"],
        stamp_duty=cfg["backtest"]["stamp_duty"],
        risk_free_rate=cfg["backtest"]["risk_free_rate"],
    )

    report = engine.run(
        start_date="20240601",
        end_date="20241231",
        factor_name="momentum_20d",
        top_n=cfg["backtest_strategy"]["top_n"],
        rebalance_freq=cfg["backtest_strategy"]["rebalance_freq"],
        enable_cost=cfg["backtest_strategy"]["enable_cost"],
        calculate_ic=cfg["backtest_strategy"]["calculate_ic"],
        benchmark_index="000300.SH",
        apply_preprocessing=True,
    )

    engine.print_report(report)


if __name__ == "__main__":
    main()
