"""线性模型加权"""
import numpy as np
import pandas as pd
from typing import Optional, List

try:
    from sklearn.linear_model import Ridge as _Ridge, Lasso as _Lasso
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


def ridge_closed_form(X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """
    Ridge: w = (X^T X + αI)^{-1} X^T y
    """
    n_features = X.shape[1]
    XTX = X.T @ X
    ridge = XTX + alpha * np.eye(n_features)
    return np.linalg.pinv(ridge) @ X.T @ y


def fit_ridge(
    panel: pd.DataFrame,
    factor_cols: List[str],
    ret_col: str = "ret",
    alpha: float = 1.0,
) -> pd.Series:
    """Ridge 回归拟合因子权重，返回 Series"""
    data = panel[factor_cols + [ret_col]].dropna()
    if data.empty:
        return pd.Series(0.0, index=factor_cols)
    X = data[factor_cols].values
    y = data[ret_col].values
    w = ridge_closed_form(X, y, alpha)
    return pd.Series(w, index=factor_cols)


def fit_lasso(
    panel: pd.DataFrame,
    factor_cols: List[str],
    ret_col: str = "ret",
    alpha: float = 1e-4,
) -> Optional[pd.Series]:
    """LASSO 回归拟合因子权重"""
    if not _HAS_SKLEARN:
        return None
    data = panel[factor_cols + [ret_col]].dropna()
    if data.empty:
        return pd.Series(0.0, index=factor_cols)
    X = data[factor_cols].values
    y = data[ret_col].values
    model = _Lasso(alpha=alpha, fit_intercept=True, max_iter=5000)
    model.fit(X, y)
    return pd.Series(model.coef_, index=factor_cols)


def auto_flip_factors(
    panel: pd.DataFrame,
    factor_cols: List[str],
    ret_col: str = "ret",
) -> tuple:
    """自动校正因子方向"""
    flipped_panel = panel.copy()
    flipped_list = []
    for col in factor_cols:
        ic = panel[col].corr(panel[ret_col])
        if ic < 0:
            flipped_panel[col] = -flipped_panel[col]
            flipped_list.append(col)
    return flipped_panel, flipped_list
