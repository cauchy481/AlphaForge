"""滚动窗口权重估计"""
import pandas as pd
from typing import Sequence

from .weights import icir_weight, normalize_weights


def compute_rolling_weights(
    panel: pd.DataFrame,
    factor_cols: Sequence[str],
    lookback: int = 60,
    min_history: int = 40,
    metric: str = "ic_ir",
) -> pd.DataFrame:
    """
    滚动窗口估计因子权重
    panel: 含 date/code/因子列/ret 的面板数据
    lookback: 回溯窗口长度（交易日）
    min_history: 最小历史数据天数
    metric: "ic" 用 IC 均值加权，"ic_ir" 用 IC IR 加权
    返回 DataFrame 含 date 和各因子权重列
    """
    dates = sorted(panel["date"].unique())
    records = []

    for idx, dt in enumerate(dates):
        start = max(0, idx - lookback)
        history_dates = dates[start:idx]
        if len(history_dates) < min_history:
            continue

        subset = panel[panel["date"].isin(history_dates)]
        if subset.empty:
            continue

        ic_means = {}
        ic_stds = {}
        for col in factor_cols:
            daily_ic = []
            for _, grp in subset.groupby("date"):
                if len(grp) < 30:
                    continue
                ic = grp[col].corr(grp["ret"], method="spearman")
                daily_ic.append(ic)
            if daily_ic:
                ic_series = pd.Series(daily_ic)
                ic_means[col] = ic_series.mean()
                ic_stds[col] = ic_series.std()
            else:
                ic_means[col] = 0.0
                ic_stds[col] = 1.0

        means_s = pd.Series(ic_means, index=factor_cols)
        stds_s = pd.Series(ic_stds, index=factor_cols)

        if metric == "ic":
            w = normalize_weights(means_s, clip_negative=False)
        else:
            w = icir_weight(means_s, stds_s)

        record = {"date": dt}
        for col in factor_cols:
            record[col] = float(w.get(col, 0.0))
        records.append(record)

    weights_df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)

    wt_cols = list(factor_cols)
    weights_df["weight_turnover"] = weights_df[wt_cols].diff().abs().sum(axis=1)

    return weights_df
