# AlphaForge： 因子库

## 目录

1. [因子注册机制](#1-因子注册机制)
2. [数据类型约定](#2-数据类型约定)
3. [因子分类](#3-因子分类)
4. [因子规范](#4-因子规范)


## 1. 因子注册机制

 `FactorRegistry` 类，位于 `registry.py`，实现了一个类级别的注册中心，所有因子通过装饰器注册。

```python
from core.factors.registry import FactorRegistry

class FactorRegistry:
    _factors: Dict[str, dict] = {}  # 全局类变量

    @classmethod
    def register(cls, name, category, description, params, required_data, lookback_days):
        """返回装饰器，同时将因子函数信息存入 _factors 字典"""
```

注册参数如下：

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 唯一标识符，如 `"momentum_20d"`，后续通过此名称调用 |
| `category` | `str` | 分类：`momentum`, `reversal`, `value`, `quality`, `volatility`, `liquidity`, `technical` |
| `description` | `str` | 描述 |
| `params` | `dict` | 默认参数，可覆盖|
| `required_data` | `List[str]` | 因子计算所需数据字段，如 `["close"]`, `["volume"]` |
| `lookback_days` | `int` | 回溯天数，用于检验和缓存预热 |

### 核心方法
```python 
 FactorRegistry.compute(name, data, date, **kwargs)
# 计算指定因子在某一截面日期的值

 FactorRegistry.get(name)
# 按名称获取因子元数据
# 返回： `dict` 含 `name`, `category`, `description`, `params`, `required_data`, `lookback_days`, `func`

FactorRegistry.list_all()
# 列出所有已注册因子

FactorRegistry.list_by_category(category)
# 按类别筛选因子

FactorRegistry.categories()
# 返回所有因子类别的列表
```




### 注册触发
触发链条大致如下：


```python
import core.factors
    → __init__.py 执行
        → from .momentum import momentum_20d, momentum_60d, ...
            → momentum.py 执行
                → @FactorRegistry.register(name="momentum_20d", ...) 被调用
                → _factors["momentum_20d"] = {...}
        → from .value import ep_ttm, ...
            → value.py 执行
                → @FactorRegistry.register(name="ep_ttm", ...) 被调用
                → _factors["ep_ttm"] = {...}
        → ... 
```


## 2. 数据类型约定

### 接口

所有因子函数接收一个 `DataLoader` 实例作为数据源，因子函数依赖以下 DataLoader 方法：

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `get_trade_calendar()` | `List[str]` | 排序后的交易日列表 `"YYYYMMDD"` |
| `get_close_price(date)` | `pd.Series` | index=股票代码, values=收盘价 |
| `get_volume(date)` | `pd.Series` | index=股票代码, values=成交量(股) |
| `get_amount(date)` | `pd.Series` | index=股票代码, values=成交额(元) |
| `get_daily_data(date)` | `pd.DataFrame` | 单日截面行情，含 code/close/open/volume/amount/pe_ttm/pb/roe 等列 |

### 返回值

- 统一返回 `pd.Series`，index 为股票代码（`str`），values 为 `float`
- 统一约定因子值越大，预期未来收益越高，所以负向因子通过取负号翻转
- **无数据时**返回空的 `pd.Series(dtype=float)`，而非 `None` 或 `NaN`
- 原始因子值需使用 `.clip(lower, upper)` 进行**极值裁剪**，以防止极端值污染
- 允许**缺失值** `NaN` 存在，后续统一处理

### 股票代码

Tushare 格式类似于 `"600000.SH"`, `"000001.SZ"`，我们在这里采用简化格式：`"600000"`, `"000001"`，为了兼容两种格式，在DataLoader 内部做了处理


## 3. 因子分类
现已简单实现了几类经典因子

### 动量类
1. 20日、60日等动量


$$\text{Momentum}\sb{20d}(t, i) = \frac{P\sb{\text{close}}(t, i) - P\sb{\text{close}}(t-20, i)}{P\sb{\text{close}}(t-20, i)}$$



2. 波动率调整动量



$$\text{VolAdjMom}\sb{20d}(t, i) = \frac{\text{Momentum}\sb{20d}(t, i)}{\sigma\sb{20d}(t, i)}$$

其中

$$\sigma\sb{20d}(t, i) = \sqrt{\frac{1}{19}\sum\sb{k=t-19}^{t} \left(r_k - \bar{r}\right)^2}$$

$$r_k = \frac{P_k - P\sb{k-1}}{P\sb{k-1}}$$ 为日收益率

这是因为原始动量因子受波动率影响大，而除以波动率相当于做 Studentization


**注意：**
具体实现中做了 winsorize 和取反




### 反转类
 

1. 5日、10日等反转


$$\text{Reversal}\sb{5d}(t, i) = -\text{Momentum}\sb{5d}(t, i) = -\frac{P\sb{\text{close}}(t, i) - P\sb{\text{close}}(t-5, i)}{P\sb{\text{close}}(t-5, i)}$$


### 价值类



1.    盈利市值比  EP `ep_ttm`



$$\text{EP}\sb{\text{TTM}}(t, i) = \frac{\text{EPS}\sb{\text{TTM}}(t, i)}{P(t, i)} = \frac{1}{\text{PE}\sb{\text{TTM}}(t, i)}$$

其中 $$\text{PE}\sb{\text{TTM}}$$ 为滚动12个月市盈率




2. 市净率倒数 BP `pb_inverse` 

$$\text{BP}(t, i) = \frac{\text{BVPS}(t, i)}{P(t, i)} = \frac{1}{\text{PB}(t, i)}$$



### 质量类



1. 净资产收益率 `roe`

$$\text{ROE}(t, i) = \frac{\text{Net Income}\sb{\text{TTM}}(t, i)}{\text{Equity}(t, i)}$$
Winsorize 到 `[-0.5, 0.5]`


### 波动率类
1. 20日、60日等波动率

$$\sigma\sb{20d}(t, i) = \sqrt{\frac{1}{19}\sum\sb{k=t-19}^{t} \left(r_k(i) - \bar{r}(i)\right)^2}$$

$$r_k(i) = \frac{P_k(i) - P\sb{k-1}(i)}{P\sb{k-1}(i)}$$



Winsorize σ 到 `[0, 0.1]`
并取负号返回



### 流动性类

1. 20日平均换手率 `turnover_20d` 

$$\text{Turnover}(t, i) = \frac{1}{20}\sum\sb{k=t-19}^{t} \frac{\text{Volume}_k(i)}{\text{Shares Outstanding}_k(i)}$$

若tushare积分不够导致`daily_basic` 接口用不了，可考虑估计

$$\text{ApproxTurnover}\sb{20d}(t, i) = \frac{1}{20}\sum\sb{k=t-19}^{t} \frac{\text{Volume}_k(i) - \text{Volume}\sb{k-1}(i)}{\text{Volume}\sb{k-1}(i)}$$



2. 20日平均成交额 `amount_20d`


$$\text{Amount}\sb{20d}(t, i) = \frac{1}{20}\sum\sb{k=t-19}^{t} \text{Amount}_k(i)$$



由于截面分布右偏，取对数 $$\text{AmtFactor}(t, i) = -\ln\left(\text{Amount}\sb{20d}(t, i)\right)$$



### 技术类
这类因子理论依据不足，所以我们只放在库中做参考
1. 相对强弱指标  `rsi_14d`


$$\text{RS}(t, i) = \frac{\text{AvgGain}\sb{14d}(t, i)}{\text{AvgLoss}\sb{14d}(t, i)}$$

其中
$$\text{AvgGain}\sb{14d} = \frac{1}{14}\sum\sb{k=t-13}^{t} \max(\Delta P_k, 0)$$
$$\text{AvgLoss}\sb{14d} = \frac{1}{14}\sum\sb{k=t-13}^{t} \max(-\Delta P_k, 0)$$

$$\text{RSI}\sb{14d}(t, i) = 100 - \frac{100}{1 + \text{RS}(t, i)}$$

因子值取

$$\text{RSIFactor}(t, i) = \frac{\text{RSI}\sb{14d}(t, i) - 50}{50}$$

标准化到 [-1, 1]



2. 乖离率 `bias_20d`



$$\text{MA}\sb{20d}(t, i) = \frac{1}{20}\sum\sb{k=t-19}^{t} P_k(i)$$

$$\text{BIAS}\sb{20d}(t, i) = \frac{P_t(i) - \text{MA}\sb{20d}(t, i)}{\text{MA}\sb{20d}(t, i)}$$


当前实现中BIAS 越高因子值越高，如要捕捉均值回复效应可以取反

winsorize 到 `[-0.3, 0.3]`



## 4. 因子规范
这里明确一下添加因子的规范：在对应类别文件下写入新的因子之后，需在 `__init__.py` 中同步
导入，这才能确保自动注册

通过如下代码快速验证：

```python
from core.factors import FactorRegistry
factor = FactorRegistry.get("my_new_factor")
print(factor["name"], factor["category"])
```

### 注意事项

1. **禁止引入未来函数**
2. 注意符号方向
3. 注意处理极端值：因子函数内部就应该 `.clip()`，不要依赖预处理通道
4. **返回值必须是对齐的 Series**：index 必须是股票代码，且与 DataLoader 返回的 index 格式一致
5. 无数据时返回空 Series`return pd.Series(dtype=float)`，不要返回 `None`
6. 将可调参数通过 `params` 字典传递，不要硬编码
7. 如需复用其他因子，必须直接导入函数，不要通过 `FactorRegistry.compute()` 调用，那样会绕过注册检查且造成循环依赖


<p align="center">
  <a href="README.md">← 返回主文档</a>
</p>
