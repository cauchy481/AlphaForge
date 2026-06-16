# AlphaForge  个人量化因子研究系统

> 面向 A 股市场的全流程因子研究与回测平台，涵盖数据管理、因子构建、预处理与中性化、因子评估、多因子合成与事件驱动回测

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

---

> 💡 若想跳过项目介绍直接上手，请前往 [快速开始](#8-快速开始) 查看运行命令，或直接浏览 [多因子分析报告示例](examples/analysis.md) 了解基于本引擎生成的示例研究

## Tushare Token 配置

整个项目统一使用 `config/settings.yaml` 管理参数

请先确保您有 [Tushare](https://tushare.pro) 账号和 token，并有足够额度支持日线数据

## 设计原则

1. 每个模块独立可测试，因子通过装饰器注册
2. 所有参数集中在 YAML 配置
3. 严格避免未来函数
4. 考虑A股实际约束

---

## 目录

1. [项目结构](#1-项目结构)
2. [系统架构](#2-系统架构)
3. [因子体系](#3-因子体系)
4. [预处理和中性化](#4-预处理和中性化)
5. [IC 分析与因子评价](#5-ic-分析与因子评价)
6. [多因子合成](#6-多因子合成)
7. [回测引擎](#7-回测引擎)
8. [快速开始](#8-快速开始)
9. [模块概览](#9-模块概览)


---

## 1. 项目结构

```
alphaforge/
├── README.md                       # 主文档
├── evaluation.md                   # IC 分析与因子评价文档
├── factors.md                      # 因子库文档
├── preprocessing_neutralizing.md   # 预处理与中性化文档
├── backtest.md                     # 回测引擎文档
├── requirements.txt
├── config/
│   └── settings.yaml               # 全局参数配置
├── core/                   
│   ├── __init__.py
│   ├── config.py                   # 配置加载
│   ├── data/
│   │   └── __init__.py             # dataLoader: Tushare + 本地缓存
│   ├── factors/
│   │   ├── __init__.py             # 触发所有因子注册
│   │   ├── registry.py             # 装饰器注册机制
│   │   ├── momentum.py             
│   │   ├── reversal.py             
│   │   ├── value.py                
│   │   ├── quality.py             
│   │   ├── volatility.py           
│   │   ├── liquidity.py           
│   │   └── technical.py           
│   ├── preprocessing/
│   │   ├── universe.py             
│   │   ├── outliers.py           
│   │   ├── missing.py            
│   │   ├── standardize.py         
│   │   ├── neutralizer.py         
│   │   └── pipeline.py            
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── ic.py                  
│   │   ├── group_return.py         
│   │   ├── turnover.py          
│   │   ├── diagnostics.py          # VIF / 相关性矩阵
│   │   ├── report.py               # 评分 / 因子择时
│   │   └── visualize.py            # 分组柱状图
│   ├── composer/
│   │   ├── __init__.py
│   │   ├── weights.py              # 等权 / IC / ICIR / 收益差加权
│   │   ├── linear.py               # Ridge  / LASSO
│   │   └── rolling.py              # 滚动窗口权重
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── engine.py              
│   │   ├── portfolio.py           
│   │   ├── performance.py         
│   │   └── cost.py                
│   ├── analytics/
│   │   └── __init__.py             # 因子贡献分解
│   └── utils/
│       ├── __init__.py             # 交易日历 / 滚动窗口
│       └── metrics.py              # 夏普 / 卡玛 / 回撤 / 信息比率
├── scripts/
│   ├── run_factor_research.py      # 因子研究入口
│   └── run_backtest.py             # 回测入口
└── tests/
    ├── conftest.py                 # 共享测试夹具
    ├── test_factors.py
    ├── test_preprocessing.py
    ├── test_evaluation.py
    ├── test_evaluation_new.py
    ├── test_composer.py
    ├── test_backtest.py
    └── test_utils.py
```

---

## 2. 系统架构
<div align="center">
  <img src="系统架构.png" width="430" height="400" />
</div>

---

## 3. 因子体系

> **[📖 因子库文档 →](factors.md)**
> 
> 因子注册机制、数据类型约定、 因子类型、 新因子开发规范

因子库实现了 **6 大类 14 个因子**：

| 大类 | 已实现因子 |
|------|-----------|
| **动量** | `momentum_20d`, `momentum_60d`, `vol_adj_momentum_20d` |
| **反转** | `reversal_5d`, `reversal_10d` |
| **价值** | `ep_ttm`, `pb_inverse` |
| **质量** | `roe` |
| **波动** | `volatility_20d`, `volatility_60d` |
| **流动性** | `turnover_20d`, `amount_20d` |
| **技术** | `rsi_14d`, `bias_20d` |

因子通过 `@FactorRegistry.register` 装饰器注册，按类别拆分到独立文件中，导入包时自动触发注册，新增因子只需在对应分类文件中编写函数并加装饰器，然后在 `__init__.py` 中同步导入即可

---

## 4. 预处理和中性化

> **[📖 预处理和中性化文档 →](preprocessing_neutralizing.md)**
>
> 详细流程、统计学性质、 参数设置

因子从原始值到可建模信号，经过固定 5 步管线：

| 步骤 | 默认方法 | 
|------|---------|
| **股票池过滤** | ST 剔除 / 次新股 / 流动性 | 
| **去极值** | MAD 法 | 
| **缺失值填充** | 三级回退（行业→市场→0） | 
| **标准化** | Z-Score | 
| **中性化** | OLS 回归取残差（行业+市值） | 

管线顺序不可交换； 代码中实现了多种方法备选（MAD/Sigma/Percentile 去极值、Z-Score/Rank/MinMax/Robust 标准化等），详见独立文档

---

## 5. IC 分析与因子评价

> **[📖 因子评估与 IC 分析文档 →](evaluation.md)**
>
> IC 分析、分组回测、稳定性分析、评分机制、因子择时

涵盖 IC 分析、分组回测、稳定性诊断和因子评分四大模块：

| 模块 | 核心指标 |
|------|---------|
| **IC 分析** | Rank IC, IC Mean/Std/IR, Win Rate, t-stat, IC Decay |
| **分组回测** | 等分分组收益、多空收益差、单调性 |
| **稳定性诊断** | 换手率、秩自相关、滚动 IC、VIF |
| **因子评分** | 综合评分公式、评级、多因子对比矩阵 |

---

## 6. 多因子合成
实现了如下方法：

| 方法 | 特点 |
|------|------|
| **等权** | 简单稳健，不依赖历史表现 |
| **IC 加权** | 奖励预测准确度 |
| **ICIR 加权** | 奖励稳定预测|
| **收益差加权** | 奖励多空区分度 |
| **Ridge (L2)** | 收缩权重，处理共线性 |
| **LASSO (L1)** | 稀疏，剔除冗余因子 |
| **滚动窗口** | 动态估计权重 |

---

## 7. 回测引擎
> **[🔧 回测引擎文档 → ](backtest.md)**
>
> 架构、数据结构、api、评价指标

采用事件驱动架构，逐日循环，在 $T$ 日，执行以下循环：

1. 盘前：因子计算，信号生成，选股 
2. 盘中调仓执行
3. 收盘：收益结算，IC分析，资金更新







---

## 8. 快速开始
>  **[示例：多因子实证分析报告 →](examples/analysis.md)**
>
> 一份基于该项目引擎实现的示例研究，基于 2024 年 A 股真实数据，包含 IC 分析、分组回测、Williams %R 研究、多因子合成与绩效对比


### 环境准备

```bash
pip install -r requirements.txt
```

### 配置 Token
```yaml
tushare:
  token: "" # your token here
```

### 运行因子研究
计算 momentum_20d, 预处理管线, 30 天 IC 序列, 生成统计报告
```bash
python scripts/run_factor_research.py
```


### 运行完整回测
下载数据，事件驱动回测，生成完整评价报告
```bash
python scripts/run_backtest.py
```

---

## 9. 模块概览

### 数据加载

```python
from core.data import DataLoader

loader = DataLoader(token="your_token", cache_dir="./data_cache")
dates = loader.get_trade_calendar("20240101", "20241231")
df = loader.get_daily_data("20240102")
close = loader.get_close_price("20240102")
```

数据按日期缓存到 `data_cache/daily/{YYYYMMDD}.csv`，后续运行直接读缓存

### 预处理
```python
from core.preprocessing import PreprocessingPipeline

pipeline = PreprocessingPipeline(
    winsorize_method="mad", winsorize_n=5.0,
    fill_method="industry_median", standardize_method="zscore",
    neutralize_method="industry_size",
    min_list_days=60, min_daily_amount=5_000_000, exclude_st=True,
)
clean_df = pipeline.run(df, date="20240102")
clean_series = pipeline.run_factor_series(factor_series, industry_series=ind)
```

### 因子评估

```python
from core.evaluation import (
    calc_ic, calc_ic_stats, compute_ic_decay,
    assign_groups, group_returns, long_short_spread, monotonicity,
    factor_turnover, stability_diagnostics,
    calc_vif, compute_composite_score, build_factor_timing,
    generate_factor_scorecard, plot_group_returns,
)

ic = calc_ic(factor_series, forward_return, method="spearman")
stats = calc_ic_stats(ic_series)
gr = group_returns(factor_series, forward_return, n_groups=10)
card = generate_factor_scorecard("momentum_20d", "momentum", ic_series, group_ret=gr)
```

### 多因子合成

```python
from core.composer import (
    equal_weight, ic_weight, icir_weight, build_composite,
    fit_ridge, fit_lasso, compute_rolling_weights,
)

w_icir = icir_weight(ic_means, ic_stds)
w_ridge = fit_ridge(panel, ["momentum_20d", "ep_ttm", "roe"], ret_col="ret", alpha=1.0)
composite_df = build_composite(panel, factor_cols, w_icir)
```

### 回测引擎

```python
from core.backtest import BacktestEngine

engine = BacktestEngine(
    data_loader=loader,
    initial_capital=1_000_000.0,
    commission_rate=0.0003, slippage_rate=0.001, stamp_duty=0.001,
)

report = engine.run(
    start_date="20240601", end_date="20241231",
    factor_name="momentum_20d", top_n=50, rebalance_freq=5,
)
engine.print_report(report)
```

### 归因分析

```python
from core.analytics import factor_contribution, brinson_attribution
contrib = factor_contribution(weights, factor_gaps)
result = brinson_attribution(portfolio_return, benchmark_return, contrib)
```


---

<p align="center">
  <i>Built by Cuachy1001</i>
</p>
