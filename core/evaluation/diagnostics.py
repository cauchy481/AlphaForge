"""多因子诊断"""
import numpy as np
import pandas as pd
from typing import Optional


def calc_correlation_matrix(
    factor_df: pd.DataFrame,
    method: str = "spearman",
) -> pd.DataFrame:
    """
    计算因子间的秩相关矩阵，用于检测冗余因子
    """
    return factor_df.corr(method=method)


def _single_vif(y: np.ndarray, X: np.ndarray) -> float:
    """
    对单个因子计算 VIF = 1 / (1 - R²)
    """
    # 添加截距
    n = len(y)
    X_design = np.column_stack([np.ones(n), X])

    try:
        # β = (X'X)⁻¹ X'y
        XtX = X_design.T @ X_design
        Xty = X_design.T @ y
        beta = np.linalg.lstsq(XtX, Xty, rcond=None)[0]
        y_hat = X_design @ beta
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        if ss_tot < 1e-15:
            return float("inf")

        r2 = 1.0 - ss_res / ss_tot
        if r2 >= 0.9999:
            return float("inf")

        return 1.0 / (1.0 - r2)
    except np.linalg.LinAlgError:
        return float("inf")


def calc_vif(
    factor_df: pd.DataFrame,
    dropna: bool = True,
) -> pd.DataFrame:
    """
    factor_df : 仅含因子列（不含 date / code）
    dropna : 是否先删除含 NaN 的行
    返回 vif_df : 含 factor / vif 两列
    """
    if dropna:
        clean = factor_df.dropna()
    else:
        clean = factor_df.copy()

    if clean.shape[1] < 2:
        return pd.DataFrame({"factor": clean.columns.tolist(), "vif": [np.nan]})

    cols = clean.columns.tolist()
    values = clean.values
    vifs = {}

    for i, col in enumerate(cols):
        y = values[:, i]
        X = np.delete(values, i, axis=1)
        vifs[col] = _single_vif(y, X)

    result = pd.DataFrame({"factor": list(vifs.keys()), "vif": list(vifs.values())})
    return result.sort_values("vif", ascending=False).reset_index(drop=True)
