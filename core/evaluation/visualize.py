"""评估可视化"""
import pandas as pd
import numpy as np
from typing import Optional


def plot_group_returns(
    group_ret: pd.Series,
    factor_name: str = "",
    figsize: tuple = (10, 5),
    title: Optional[str] = None,
    save_path: Optional[str] = None,
):
   
    try:
        import matplotlib
        matplotlib.use("Agg")  
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("需要安装 matplotlib: pip install matplotlib")

    import matplotlib.colors as mcolors

    valid = group_ret.dropna()
    if valid.empty:
        raise ValueError("group_ret 全部为 NaN，无法绘图")

    n = len(valid)
    groups = valid.index.tolist()
    values = valid.values

    # 颜色
    colors = mcolors.LinearSegmentedColormap.from_list(
        "q_gradient",
        [(0.85, 0.15, 0.15), (0.95, 0.95, 0.95), (0.15, 0.65, 0.15)],
        N=n,
    )(np.linspace(0, 1, n))

    fig, ax = plt.subplots(figsize=figsize)

    bars = ax.bar(range(n), values, color=colors, edgecolor="white", linewidth=0.5)

    # 零线
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--", zorder=2)

    # 柱顶标注数值
    for i, (g, v) in enumerate(zip(groups, values)):
        va = "bottom" if v >= 0 else "top"
        offset = abs(v) * 0.03 + 0.0001
        y_pos = v + offset if v >= 0 else v - offset
        ax.text(i, y_pos, f"{v*100:.2f}%", ha="center", va=va, fontsize=8)

    ax.set_xticks(range(n))
    ax.set_xticklabels([f"Q{int(g)}" for g in groups], fontsize=9)
    ax.set_xlabel("Factor Quantile", fontsize=10)
    ax.set_ylabel("Mean Forward Return", fontsize=10)

    if title is None:
        ls_spread = values[-1] - values[0] if len(values) >= 2 else np.nan
        title = f"Group Return — {factor_name}" if factor_name else "Group Return by Factor Quantile"
        if not np.isnan(ls_spread):
            title += f"\nLong-Short Spread: {ls_spread*100:.2f}%"

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    elif matplotlib.get_backend() != "Agg":
        plt.show()
    else:
        plt.close(fig)

    return fig, ax
