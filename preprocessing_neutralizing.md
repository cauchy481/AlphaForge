# AlphaForge：预处理与中性化方法
  

## 目录

1. [管线概览](#1-管线概览)
2. [股票池过滤](#2-股票池过滤)
3. [去极值处理](#3-去极值处理)
4. [缺失值填充](#4-缺失值填充)
5. [因子标准化](#5-因子标准化)
6. [因子中性化](#6-因子中性化)
7. [配置参数](#7-配置参数)


## 1. 管线概览
设计如下步骤：
1. 过滤剔除不可交易的股票（ST、次新股、停牌、涨跌停）
2. 异常值处理
3. 缺失值填充
4. 标准化
5. 中性化


### PreprocessingPipeline 类

```python
from core.preprocessing import PreprocessingPipeline

pipeline = PreprocessingPipeline(
    winsorize_method="mad",
    winsorize_n=5.0,
    fill_method="industry_median",
    standardize_method="zscore",
    neutralize_method="industry_size",
    min_list_days=60,
    min_daily_amount=5_000_000,
    exclude_st=True,
)

# 全管线：DataFrame in，DataFrame out
clean_df = pipeline.run(df, date="20240102")

# 单因子快捷接口：Series in，Series out
clean_series = pipeline.run_factor_series(
    factor_series,
    industry_series=industry_series,
)
```


## 2. 股票池过滤


#### ST / *ST 股票剔除

ST 股票连续亏损或存在重大违规，基本面恶化的路径与正常股票不同，其因子行为不具有泛化性；而且 ST 股票实行涨跌幅限制，风险特征显著不同

#### 次新股过滤
新股上市初期价格波动异常；历史数据不足，一些因子无法计算；有涨停板限制

#### 流动性过滤
日成交额过低的股票无法以合理价格成交；流动性不足导致滑点远大于估计值，回测结果不可靠


## 3. 去极值处理

这里我们实现了三种基础方法：MAD, $3\sigma$, 分位数

### MAD 方法

基于对方差的稳健估计，在heavy tail下更加鲁棒，下面给出方法和证明

设 $\tilde{x}$ 为样本中位数，定义中位数绝对偏差：

$$\text{MAD} = \text{median}\left(\left|x_i - \tilde{x}\right|\right)$$

Winsorization 边界为：

$$L = \tilde{x} - k \cdot b \cdot \text{MAD}$$
$$U = \tilde{x} + k \cdot b \cdot \text{MAD}$$

其中 $b = 1.4826$ 是**一致性常数**

#### Proof
假设数据来自正态分布 $X \sim \mathcal{N}(\mu, \sigma^2)$，则由一致性，中位数 $\tilde{X} \to \mu$
$$\text{median}\left(\left|x - \tilde{x}\right|\right) = \sigma \cdot \text{median}\left(\frac{\left|x - \tilde{x}\right|}{\sigma}\right) =:\sigma z_M
$$
$$P\left(\frac{\left|x - \tilde{x}\right|}{\sigma}\leq  z_M \right)=2\Phi(z_M)-1=0.5
$$


$$b = \frac{1}{\Phi^{-1}(0.75)} \approx \frac{1}{0.6745} \approx 1.4826$$

因此 $b \cdot \text{MAD} \xrightarrow{p} \sigma$



### Sigma 方法

$$L = \bar{x} - k \cdot s, \quad U = \bar{x} + k \cdot s$$

其中 $\bar{x}$ 为样本均值，$s$ 为样本标准差
该方法比较简便，但异常值本身会拉大 $\sigma$, 造成漏检
 
### 3.4 Percentile 方法

$$L = Q_{c/2}, \quad U = Q_{1 - c/2}$$

其中 $Q_p$ 为第 $p$ 分位数

该方法不受极端值影响，但是截取比例固定，要先根据分布情况进行估计



## 4. 缺失值填充

设 $\mathbf{R}$ 为缺失指示矩阵（$R_{ij} = 1$ 若 $x_{ij}$ 缺失），$\mathbf{X}_{\mathrm{obs}}$ 为观测值，$\mathbf{X}_{\mathrm{mis}}$ 为缺失值：

- **MCAR** (Missing Completely At Random)：$P(\mathbf{R} \mid \mathbf{X}_{\mathrm{obs}}, \mathbf{X}_{\mathrm{mis}}) = P(\mathbf{R})$
- **MAR** (Missing At Random)：$P(\mathbf{R} \mid \mathbf{X}_{\mathrm{obs}}, \mathbf{X}_{\mathrm{mis}}) = P(\mathbf{R} \mid \mathbf{X}_{\mathrm{obs}})$
- **MNAR** (Missing Not At Random)：$P(\mathbf{R} \mid \mathbf{X}_{\mathrm{obs}}, \mathbf{X}_{\mathrm{mis}}) \neq P(\mathbf{R} \mid \mathbf{X}_{\mathrm{obs}})$

该项目暂时不考虑 MNAR

具体实现中使用三级回退：

1. 若某行业有非缺失值，使用该行业中位数
2. 若某行业全部缺失或没有行业分类信息，回退到截面中位数
3. 若整截面全为 NaN，填充 0 并标记



## 5. 因子标准化
这里我们给出四种方法

### Z-Score 

$$z_i = \frac{x_i - \bar{x}}{s}$$

其中 $s^2 = \frac{1}{n-1}\sum_{i=1}^{n} (x_i - \bar{x})^2$

变换后具有如下性质：
- $\mathbb{E}[Z] = 0$，$\mathrm{Var}(Z) = 1$
- 保持原始分布的偏度和峰度
- 若 $X$ 为正态分布，则 $Z \sim \mathcal{N}(0, 1)$

因此适用于近似对称分布的因子，例如动量或者反转

### Rank 

$$z_i = \frac{r_i - 1}{n - 1}$$

其中 $r_i = \text{Rank}(x_i)$（从小到大）

性质如下：
- $Z \sim \text{Uniform}[0, 1]$
- **完全消除了偏度和峰度**
- 极端值效应被压缩到边界



### MinMax 

$$z_i = \frac{x_i - \min(x)}{\max(x) - \min(x)}$$

分布性质： $Z \in [0, 1]$

但是显然该方法对极端值极度敏感，使用前要去极值

### Robust标准化

$$z_i = \frac{x_i - \tilde{x}}{\text{MAD}}$$

其中 $\tilde{x}$ 为中位数

分布性质：
- 近似零中心
- 鲁棒性高（BDP = 50%）




## 6. 因子中性化

该项目采用线性回归来实现中性化

设 $\mathbf{f} \in \mathbb{R}^n$ 为 $n$ 只股票在某个截面上的原始因子向量，$\mathbf{X} \in \mathbb{R}^{n \times p}$ 为风险因子载荷矩阵（含截距），建立横截面回归：

$$\mathbf{f} = \mathbf{X}\boldsymbol{\beta} + \boldsymbol{\varepsilon}$$

其中：
- $\mathbf{X}$ 的列包括：截距项 $\mathbf{1}$，对数市值 $\ln(\mathrm{Size})$，以及行业哑变量 $\mathbf{I}_1, \ldots, \mathbf{I}_{K-1}$
- $\boldsymbol{\beta} \in \mathbb{R}^p$ 为回归系数
- $\boldsymbol{\varepsilon} \in \mathbb{R}^n$ 为残差项

中性化后的因子值为残差：

$$\hat{\mathbf{f}}_{\mathrm{neutral}} = \hat{\boldsymbol{\varepsilon}} = \mathbf{f} - \mathbf{X}\hat{\boldsymbol{\beta}}$$

其中 $\hat{\boldsymbol{\beta}} = (\mathbf{X}^\top \mathbf{X})^{-1} \mathbf{X}^\top \mathbf{f}$ 为 OLS 估计量

不难得到下面的性质：

1. 正交性

$$\mathbf{X}^\top \hat{\mathbf{f}}_{\mathrm{neutral}} = \mathbf{0}$$


2. **方差分解**：

$$\mathrm{Var}(\mathbf{f}) = \mathrm{Var}(\mathbf{X}\hat{\boldsymbol{\beta}}) + \mathrm{Var}(\hat{\boldsymbol{\varepsilon}})$$



### 设计矩阵构造

行业分类为 $K$ 个行业，我们引入 $K-1$ 个哑变量，基准行业的哑变量为全0：

$$\mathbf{I}_{k}(i) = \begin{cases} 1 & \text{股票 i 属于行业 k} \\ 0 & \text{其他} \end{cases}, \quad k = 1, \ldots, K-1$$

使用对数市值作为连续协变量：

$$\mathrm{Size}(i) = \ln\left(\mathrm{MarketCap}(i)\right)$$


设计矩阵 $\mathbf{X}$ 可能存在共线性，某些行业与市值高度相关，例如银行业市值普遍较大, 这里使用 VIF 来评判：$$\mathrm{VIF}_j = \frac{1}{1 - R_j^2}$$，

当 $\text{VIF}$ 较大，考虑删除因子；
当 $\max(\text{VIF}_j) > 10$ 时，使用 Ridge 回归替代 OLS：

$$\hat{\boldsymbol{\beta}}_{\text{ridge}} = (\mathbf{X}^\top \mathbf{X} + \lambda \mathbf{I})^{-1} \mathbf{X}^\top \mathbf{f}$$

###  中性化方案

本项目采用行业 + 市值中性化 (`"industry_size"`) 

$$\mathbf{f} = \alpha + \beta_1 \cdot \ln(\mathrm{Size}) + \sum_{k=1}^{K-1} \gamma_k \mathbf{I}_k + \boldsymbol{\varepsilon}$$


另外，本项目支持 Barra格式数据，因此也可以采用 Barra 全风格中性化 (`"barra"`)

$$\mathbf{f} = \alpha + \sum_{j=1}^{10} \beta_j \cdot \mathrm{BarraStyle}_j + \sum_{k=1}^{K-1} \gamma_k \mathbf{I}_k + \boldsymbol{\varepsilon}$$

但相关数据需额外导入


由正交性条件，截距项会导出 $\sum\epsilon_i=0$, 因此可以在一开始就对 $f$ 和 $s$ 做中心化处理

下面我们考虑只做市值中性化，不分行业，那么就是求解
：
$$ s \perp f_{\mathrm{neutral}} = f - \hat{\beta} \cdot s  $$
得到 $\hat{\beta} = \frac{\mathrm{Cov}(f, s)}{\mathrm{Var}(s)}$




## 7. 配置参数

所有参数在 `config/settings.yaml` 中配置：

```yaml
preprocessing:
  winsorize_method: "mad"        # mad / sigma / percentile
  winsorize_n: 5.0               
  fill_method: "industry_median" # industry_median / median / zero / drop
  standardize_method: "zscore"   # zscore / rank / minmax / robust
  neutralize_method: "industry_size"  # none / industry / size / industry_size / barra

universe:
  min_list_days: 60              # 上市最少日历日
  min_daily_amount: 5000000      # 最小日均成交额（元）
  exclude_st: true               # 是否剔除 ST
```



## 参考资料

1. Hampel, F. R. (1974). The influence curve and its role in robust estimation. *Journal of the American Statistical Association*.
2. Rousseeuw, P. J., & Croux, C. (1993). Alternatives to the median absolute deviation. *Journal of the American Statistical Association*.
3. Rubin, D. B. (1976). Inference and missing data. *Biometrika*.
4. Menchero, J., et al. (2011). *MSCI Barra Global Equity Risk Model*.
5. Fama, E. F., & French, K. R. (1992). The cross-section of expected stock returns. *Journal of Finance*.
6. Grinold, R. C., & Kahn, R. N. (2000). *Active Portfolio Management*.
7. Frisch, R., & Waugh, F. V. (1933). Partial time regressions as compared with individual trends. *Econometrica*.
8. Lovell, M. C. (1963). Seasonal adjustment of economic time series. *Journal of the American Statistical Association*.


<p align="center">
  <a href="README.md">← 返回主文档</a>
</p>
