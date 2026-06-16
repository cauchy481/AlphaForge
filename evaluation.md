# AlphaForge：IC 分析与因子评价体系


## 目录

1. [IC 分析](#1-ic-分析)
2. [分组回测](#2-分组回测)
3. [稳定性分析](#3-稳定性分析)
4. [评分](#4-评分)
5. [因子择时](#5-因子择时)


## API 

```python
from core.evaluation import (
    # IC 分析
    calc_ic,              # 单日 IC Rank/Pearson
    calc_ic_stats,         # 统计量
    compute_ic_series,     # 批量计算 IC 序列
    compute_ic_decay,      # 衰减分析

    # 分组回测
    assign_groups,         # 等分分组
    group_returns,         # 分组收益
    long_short_spread,     # 多空收益差
    monotonicity,          # 单调性系数

    # 稳定性
    factor_turnover,       # 名单换手率
    factor_autocorr,       # 因子自相关
    stability_diagnostics, # 滚动 IC 检测
    calc_vif,              # VIF 共线性诊断
    calc_correlation_matrix,  # 因子相关矩阵

    # 评分
    generate_factor_scorecard,  # 单因子评分
    compare_factors,            # 多因子对比矩阵
    compute_composite_score,    # 综合加权得分

    # 择时
    build_factor_timing,   # 滚动 IC/IR 择时信号

    # 可视化
    plot_group_returns,    # 分组收益柱状图
)
```
## 1. IC 分析

我们使用 **Information Coefficient (IC)** 作为基本指标

设 $\mathbf{f}_t \in \mathbb{R}^n$ 为 $t$ 日 $n$ 只股票的因子值向量，$\mathbf{r}_{t+1} \in \mathbb{R}^n$ 为 $t \to t+1$ 的 forward return：

$$\text{IC}_t = \text{Corr}\left(\mathbf{f}_t,\; \mathbf{r}_{t+1}\right)$$


实现层面我们使用 **Rank IC** 为主， 同时避免未来函数


### IC 统计指标

将每日 IC 序列 $\{\text{IC}_1, \text{IC}_2, \ldots, \text{IC}_T\}$ 聚合为标准指标：

| 指标 | 公式 | 
|------|------|
| **IC Mean** | $\bar{\text{IC}} = \frac{1}{T}\sum \text{IC}_t$ | 
| **IC Std** | $\sigma_{\text{IC}} = \sqrt{\frac{1}{T}\sum (\text{IC}_t - \bar{\text{IC}})^2}$ | 
| **IC IR** | $\text{IR} = \bar{\text{IC}} / \sigma_{\text{IC}}$ | 
| **IC Win Rate** | $\frac{\#\{\text{IC}_t > 0\}}{T}$ | 
| **IC t-stat** | $t = \bar{\text{IC}} / (\sigma_{\text{IC}} / \sqrt{T})$ | 


注意：IC t-stat 假设 IC 序列是i.i.d.的，但数据通常不满足此假设，因此 $t$ 检验只做参考



### IC 衰减分析

IC 衰减衡量因子的预测力随持有期延长的变化：

$$\text{IC Decay}(h) = \text{Corr}\left(\mathbf{f}_t,\; \mathbf{r}_{t \to t+h}\right), \quad h = 1, 5, 10, 20, \ldots$$

其中 $\mathbf{r}_{t \to t+h}$ 为 $h$ 日 forward return

IC 衰减决定调仓频率，进而影响成本和容量


- **衰减快**（如反转因子）：预测力短，必须高频调仓
- **衰减慢**（如价值因子）：预测力长，可以低调仓


## 2. 分组回测
IC 高的因子可能只在头部有效， 或者存在非单调关系，因此我们需要分组回测，代码中实现如下：

1. 每期按因子值将股票等分为 $N$ 组，每组数量大致相等
2. 计算每组等权组合的下期平均收益
3. 检验 Q1 → QN（低到高）的单调性
4. 多空收益差 = QN 收益 - Q1 收益
5. 绘制分组柱状图

```python
from core.evaluation import assign_groups, group_returns, long_short_spread

groups = assign_groups(factor_series, n_groups=10)
group_ret = group_returns(factor_series, forward_return, n_groups=10)
spread = long_short_spread(group_ret)   
```


### 单调性检验

计算组号与组收益的 Spearman 秩相关：

$$\text{Monotonicity} = \rho_s\left(\{1, 2, \ldots, N\},\; \{\bar{r}_1, \bar{r}_2, \ldots, \bar{r}_N\}\right)$$



## 3. 稳定性分析

即使 IC 和分组收益很好，因子也可能因为不稳定而失败，所以下面进行稳定性检验

### 换手率（Turnover）
通过相邻两日因子值的**秩自相关**（Rank Autocorrelation）来估计：

$$\text{Rank Autocorr}_t = \rho_s\left(\mathbf{f}_{t-1},\; \mathbf{f}_t\right)$$

$$\text{Turnover} \approx 1 - \text{Rank Autocorr}$$



注意：如果基本面因子的 Rank Autocorr 突然变得很低，通常说明数据有问题

### 滚动 IC 稳定性

计算滚动窗口的 IC 均值和 IR，观察因子是否在时间上持续有效：

```python
roll_mean = ic_series.rolling(60).mean()   
roll_ir   = roll_mean / ic_series.rolling(60).std()  
```


### VIF 

$$\text{VIF}_j = \frac{1}{1 - R_j^2}$$

其中 $R_j^2$ 是因子 $j$ 对其他所有因子回归的 R²

我们采取如下标准：
| VIF | 判断 |
|-----|------|
| < 5 | 正常，可接受 |
| 5–10 | 中等共线性，需要关注 |
| > 10 | 严重共线性，需要剔除或正交化 |


## 4. 评分

我们实现了两种综合评分 metrics
1. 综合加权
$$
\text{Score} = 0.40 × \text{IC\_IR}      
         + 0.20 × \text{IC\_Mean}     
         + 0.20 × \text{Monotonicity} 
         + 0.20 × (1 - \text{Turnover})  
$$

2. 等级赋分

基于 IC 统计自动评级（`evaluation/report.py` → `_assign_rating()`）

| 条件 | 得分 |
|------|------|
| $\vert\text{IR}\vert > 0.75$ | +3 |
| $\vert\text{IR}\vert > 0.5$ | +2 |
| $\vert\text{IR}\vert > 0.3$ | +1 |
| t-stat > 3.0 | +2 |
| t-stat > 2.0 | +1 |
| Win Rate > 58% | +2 |
| Win Rate > 53% | +1 |



## 5. 因子择时

因子表现不是恒定不变的, 因此我们滚动监控 IC/IR 的信号，在因子失效期暂时停用


$$\text{FactorOn}_t = \begin{cases} 1 & \text{Roll\_Mean}_t > 0 \;\text{and}\; \text{Roll\_IR}_t > \theta \\ 0 & \text{otherwise} \end{cases}$$

关键注意两点：严禁引入未来信息；阈值 $\theta$ 需要在样本外验证



## 参考资料

1. Grinold, R. C., & Kahn, R. N. (2000). *Active Portfolio Management*.
2. Qian, E. E., Hua, R. H., & Sorensen, E. H. (2007). *Quantitative Equity Portfolio Management*. 
3. Jegadeesh, N., & Titman, S. (1993). Returns to buying winners and selling losers. *Journal of Finance*. 
4. Fama, E. F., & French, K. R. (1992). The cross-section of expected stock returns. *Journal of Finance*.


<p align="center">
  <a href="README.md">← 返回主文档</a>
</p>