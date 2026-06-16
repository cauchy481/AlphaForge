"""因子评估模块入口"""
from .ic import calc_ic, calc_ic_stats, compute_ic_series, compute_ic_decay
from .group_return import assign_groups, group_returns, long_short_spread, monotonicity
from .turnover import factor_turnover, factor_autocorr, rank_autocorr, turnover_series, stability_diagnostics
from .report import generate_factor_scorecard, compare_factors, compute_composite_score, build_factor_timing
from .diagnostics import calc_correlation_matrix, calc_vif
from .visualize import plot_group_returns
