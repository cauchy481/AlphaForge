"""多因子合成模块入口"""
from .weights import (
    normalize_weights,
    equal_weight,
    ic_weight,
    icir_weight,
    ret_spread_weight,
    compute_factor_metrics,
    build_composite,
)
from .linear import ridge_closed_form, fit_ridge, fit_lasso, auto_flip_factors
from .rolling import compute_rolling_weights
