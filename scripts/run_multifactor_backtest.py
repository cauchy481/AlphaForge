"""多因子合成回测"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from core.config import load_config
from core.data import DataLoader
from core.factors import FactorRegistry
from core.preprocessing import PreprocessingPipeline
from core.composer import icir_weight, equal_weight
from core.backtest import BacktestEngine


def main():
    cfg = load_config()

    loader = DataLoader(token=cfg["tushare"]["token"], cache_dir=cfg["data"]["cache_dir"])
    pipeline = PreprocessingPipeline(
        winsorize_method=cfg["preprocessing"]["winsorize_method"],
        standardize_method=cfg["preprocessing"]["standardize_method"],
        neutralize_method=cfg["preprocessing"]["neutralize_method"],
    )

    dates = loader.get_trade_calendar("20240102", "20240331")
    print(f"交易日范围: {dates[0]} ~ {dates[-1]}, 共 {len(dates)} 天")

    factor_names = ["momentum_20d", "reversal_5d"]
    print(f"候选因子: {factor_names}")

    WARMUP = 40
    print(f"\n[1] 估计因子权重 (前 {WARMUP} 天 ICIR)")
    warmup_dates = dates[:WARMUP]
    ic_records = {name: [] for name in factor_names}

    for i in range(1, len(warmup_dates)):
        dt = warmup_dates[i]
        prev_dt = warmup_dates[i - 1]
        ret_df = loader.get_daily_data(dt)
        if ret_df.empty:
            continue
        if "code" not in ret_df.columns and "ts_code" in ret_df.columns:
            ret_df["code"] = ret_df["ts_code"]
        ret_series = ret_df.set_index("code")["pct_chg"].astype(float) / 100.0

        for name in factor_names:
            f = FactorRegistry.compute(name, loader, prev_dt)
            if f.empty:
                continue
            ic = f.dropna().corr(ret_series.dropna(), method="spearman")
            if not np.isnan(ic):
                ic_records[name].append(ic)

    ic_means = pd.Series({k: np.mean(v) if v else np.nan for k, v in ic_records.items()})
    ic_stds = pd.Series({k: np.std(v) if v else np.nan for k, v in ic_records.items()})
    print(f"  IC Mean: {dict(ic_means.round(4))}")
    print(f"  IC Std:  {dict(ic_stds.round(4))}")

    # ICIR 权重
    weights = icir_weight(ic_means, ic_stds)
    if weights.abs().sum() == 0:
        weights = equal_weight(factor_names)
    print(f"  权重:     {dict(weights.round(3))}")

    print(f"\n[2] 构建合成因子 (第 {WARMUP} 天之后)")
    composite_values = {}
    backtest_dates = dates[WARMUP:]
    skipped = 0

    for dt in backtest_dates:
        day_factors = {}
        for name in factor_names:
            f = FactorRegistry.compute(name, loader, dt)
            if not f.empty:
                clean = pipeline.run_factor_series(f)
                day_factors[name] = clean

        if len(day_factors) < len(factor_names):
            skipped += 1
            continue

        # 对齐索引
        common_idx = day_factors[factor_names[0]].index
        for s in list(day_factors.values())[1:]:
            common_idx = common_idx.intersection(s.index)
        if len(common_idx) < 50:
            skipped += 1
            continue

        # 加权合成
        composite = pd.Series(0.0, index=common_idx)
        for name, w in weights.items():
            composite += w * day_factors[name].reindex(common_idx)

        composite_values[dt] = composite

    print(f"  合成因子覆盖: {len(composite_values)} 天, 跳过: {skipped}")

    # 回测
    print("\n[3] 运行多因子回测...")
    engine = BacktestEngine(
        data_loader=loader,
        initial_capital=cfg["backtest"]["initial_capital"],
        commission_rate=cfg["backtest"]["commission_rate"],
        slippage_rate=cfg["backtest"]["slippage_rate"],
        stamp_duty=cfg["backtest"]["stamp_duty"],
        risk_free_rate=cfg["backtest"]["risk_free_rate"],
    )

    report = engine.run(
        start_date=backtest_dates[0],
        end_date=backtest_dates[-1],
        factor_name="composite(momentum+ep+roe)",
        factor_values=composite_values,
        top_n=cfg["backtest_strategy"]["top_n"],
        rebalance_freq=cfg["backtest_strategy"]["rebalance_freq"],
        enable_cost=cfg["backtest_strategy"]["enable_cost"],
        calculate_ic=cfg["backtest_strategy"]["calculate_ic"],
    )

    engine.print_report(report)


if __name__ == "__main__":
    main()
