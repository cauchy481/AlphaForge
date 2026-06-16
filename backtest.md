# AlphaForge： 回测引擎

## 目录

1. [架构](#1-架构)
2. [API](#2-api)
3. [指标](#3-指标)


## 1. 架构

回测引擎由四个类构成，由 `BacktestEngine` 统一调度

```
BacktestEngine.run()                    
    ├── Portfolio              
    ├── Performance            
    └── Cost                      
```

逐日循环的 pseudocode 如下：

```
for dt in trade_dates:
    prev_dt = trade_dates[i-1]         

    ── 盘前 ──
    factor = FactorRegistry.compute(name, loader, prev_dt)    # 用 T-1 日收盘数据
    signal = factor.nlargest(top_n)                           # Top N 选股

    ── 盘中 ──
    if 调仓日:
        PortfolioManager.rebalance(signal)                    # 计算换手 + 成本

    ── 盘后 ──
    ret = 持仓等权平均(pct_chg / 100)                        
    PortfolioManager.update_capital(ret)                      # 复利累积
    ic = Corr(Factor_{T-1}, pct_chg_T)                        # Rank IC
```

**对齐：** 因子用 T-1 日收盘数据计算，收益用 T 日 `pct_chg`








## 2. API

### BacktestEngine

```python
from core.backtest import BacktestEngine

engine = BacktestEngine(
    data_loader=loader,
    initial_capital=1_000_000.0,
    commission_rate=0.0003,
    slippage_rate=0.001,
    stamp_duty=0.001,
    risk_free_rate=0.03,
)

report = engine.run(
    start_date="20240601",
    end_date="20241231",
    factor_name="momentum_20d",
    top_n=50,
    rebalance_freq=5,
)
engine.print_report(report)
```
`run()` 返回一个 `dict`：

```python
{
    "total_return":        float,     
    "annual_return":       float,     
    "annual_volatility":   float,    
    "sharpe_ratio":        float,    
    "max_drawdown":        float,     
    "calmar_ratio":        float,    
    "win_rate":            float,     
    "cumulative_returns":  Series,    
    "daily_returns":       Series,   

    # 当 calculate_ic=True 时包含
    "ic_mean":             float,     
    "ic_std":              float,     
    "ir":                  float,     
    "ic_win_rate":         float,     

    # 交易统计
    "total_cost":          float,     
    "trade_count":         int,       
    "avg_turnover":        float,     
    "ic_series":           Series,    
}
```
### Portfolio

```python
from core.backtest import PortfolioManager

pm = PortfolioManager(
    initial_capital=1_000_000.0,
    commission_rate=0.0003,
    slippage_rate=0.001,
    stamp_duty=0.001,
)

# 调仓：传入目标持仓列表，返回换手率和交易成本
info = pm.rebalance(["000001", "600000", ...])

# 日收益更新
pm.update_capital(0.005)  

# 查询
pm.current_holdings   # 当前持仓
pm.current_capital    # 当前资金
```

### Cost

```python
from core.backtest import CostModel

cost = CostModel(commission_rate=0.0003, slippage_rate=0.001, stamp_duty=0.001)

cost.buy_cost_rate()         # 0.0013 
cost.sell_cost_rate()        # 0.0023  
cost.roundtrip_cost_rate()   # 0.0036 
```

### Performance

```python
from core.backtest import PerformanceEvaluator

eval = PerformanceEvaluator(risk_free_rate=0.03)

# 绩效报告
report = eval.generate_report(cumulative_returns, daily_returns)

# 单日 IC
ic = eval.calculate_ic(factor_series, forward_return)

# IC 序列统计
stats = eval.calculate_ic_ir(ic_series)
```


## 3. 指标

### 绩效指标

| 指标 | 计算公式 |
|------|---------|
| **累计收益** | $\displaystyle \text{CumRet} = \prod_{i=1}^{T}(1+r_i) - 1$ |
| **年化收益** | $\displaystyle R_{\text{annual}} = (1+\text{CumRet})^{\frac{252}{T}} - 1$ |
| **年化波动** | $\displaystyle \sigma_{\text{annual}} = \sigma_{\text{daily}} \times \sqrt{252}$ |
| **夏普比率** | $\displaystyle \text{Sharpe} = \frac{R_{\text{annual}} - R_f}{\sigma_{\text{annual}}}$ |
| **最大回撤** | $\displaystyle \text{MDD} = \min_{t}\left(\frac{\text{NAV}_t}{\max_{s \le t}\text{NAV}_s} - 1\right)$ |
| **卡玛比率** | $\displaystyle \text{Calmar} = \frac{R_{\text{annual}}}{\lvert \text{MDD} \rvert}$ |
| **胜率** | $\displaystyle \text{WinRate} = \frac{\#\{r_i > 0\}}{T}$ |

### IC 指标

| 指标 | 计算公式 |
|------|---------|
| **IC Mean** | $\displaystyle \overline{\text{IC}} = \frac{1}{T}\sum_{t=1}^{T} \text{IC}_t$ |
| **IC Std** | $\displaystyle \sigma_{\text{IC}} = \sqrt{\frac{1}{T}\sum_{t=1}^{T}\left(\text{IC}_t - \overline{\text{IC}}\right)^2}$ |
| **IC IR** | $\displaystyle \text{IR} = \frac{\overline{\text{IC}}}{\sigma_{\text{IC}}}$ |
| **IC Win Rate** | $\displaystyle \text{IC WinRate} = \frac{\#\{\text{IC}_t > 0\}}{T}$ |

其中单日 IC 定义：

$$
\text{IC}_t = \text{Corr}\!\left(\text{Rank}(f_{t-1}),\ \text{Rank}(r_t)\right)
$$

### 交易统计

| 指标 | 计算公式 |
|------|---------|
| **换手率** | $\displaystyle \text{Turnover} = \frac{N_{\text{buy}} + N_{\text{sell}}}{2 \times N_{\text{hold}}} \in [0,1]$ |
| **交易成本** | $\displaystyle \text{Cost} = \sum_{k}\left(c_{\text{comm}} + c_{\text{stamp}}\cdot\mathbb{1}_{\text{sell}} + c_{\text{slip}}\right)\cdot V_k$ |
| **交易笔数** | $\displaystyle N_{\text{trade}} $ |

### 成本模型

| 费用 | 费率 | 方向 |
|------|------|------|
| 佣金 $c_{\text{comm}}$ | $0.03\%$ | 买卖双向 |
| 印花税 $c_{\text{stamp}}$ | $0.1\%$ | 卖出 |
| 滑点 $c_{\text{slip}}$ | $0.1\%$ | 买卖双向 |

其中各方向成本费率：

$$
\begin{aligned}
c_{\text{buy}} &= c_{\text{comm}} + c_{\text{slip}} = 0.13\% \\
c_{\text{sell}} &= c_{\text{comm}} + c_{\text{slip}} + c_{\text{stamp}} = 0.23\% \\
c_{\text{roundtrip}} &= c_{\text{buy}} + c_{\text{sell}} = 0.36\%
\end{aligned}
$$


<p align="center">
  <a href="README.md">← 返回主文档</a>
</p>