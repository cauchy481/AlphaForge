"""因子研究入口"""
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from core.config import load_config
from core.data import DataLoader
from core.factors import FactorRegistry
from core.preprocessing import PreprocessingPipeline
from core.evaluation import calc_ic, calc_ic_stats


def main():
    cfg = load_config()

    loader = DataLoader(
        token=cfg["tushare"]["token"],
        cache_dir=cfg["data"]["cache_dir"],
    )

    dates = loader.get_trade_calendar("20240101", "20241231")
    if not dates:
        print("无可用交易日，请先下载数据")
        return

    test_date = dates[120]  # 取第120个交易日做演示
    print(f"测试日期: {test_date}")

    factor_name = "momentum_20d"
    factor_series = FactorRegistry.compute(factor_name, loader, test_date)
    print(f"\n{factor_name} 因子计算完成: {factor_series.dropna().count()} 只股票")

    pipeline = PreprocessingPipeline(
        winsorize_method=cfg["preprocessing"]["winsorize_method"],
        standardize_method=cfg["preprocessing"]["standardize_method"],
        neutralize_method=cfg["preprocessing"]["neutralize_method"],
    )
    clean = pipeline.run_factor_series(factor_series)
    print(f"预处理后因子: min={clean.min():.3f}, max={clean.max():.3f}, std={clean.std():.3f}")

    print("\n计算全区间 IC...")
    ic_values = []
    for i in range(1, min(31, len(dates))):  # 演示只算30天
        dt = dates[i]                         
        prev_dt = dates[i - 1]                

        f = FactorRegistry.compute(factor_name, loader, prev_dt) 
        ret_df = loader.get_daily_data(dt)                        
        if f.empty or ret_df.empty:
            continue
        if "code" not in ret_df.columns and "ts_code" in ret_df.columns:
            ret_df["code"] = ret_df["ts_code"]
        ret_series = ret_df.set_index("code")["pct_chg"].astype(float) / 100.0
        ic = calc_ic(f, ret_series)
        if not np.isnan(ic):
            ic_values.append(ic)

    ic_series = pd.Series(ic_values)
    stats = calc_ic_stats(ic_series)
    print(f"IC Mean: {stats['ic_mean']:.4f}")
    print(f"IC IR:   {stats['ic_ir']:.4f}")
    print(f"IC Win:  {stats['ic_win_rate']:.2%}")
    print(f"IC t:    {stats['ic_t']:.2f}")


if __name__ == "__main__":
    main()
