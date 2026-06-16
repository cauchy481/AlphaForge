"""因子模块入口"""
from .registry import FactorRegistry

# 按类别分别导入，触发 @FactorRegistry.register 装饰器
from .momentum import (   # noqa: F401, E402
    momentum_20d,
    momentum_60d,
    vol_adj_momentum,
)
from .reversal import (   # noqa: F401, E402
    reversal_5d,
    reversal_10d,
)
from .value import (      # noqa: F401, E402
    ep_ttm,
    pb_inverse,
)
from .quality import (    # noqa: F401, E402
    roe,
)
from .volatility import ( # noqa: F401, E402
    volatility_20d,
    volatility_60d,
)
from .liquidity import (  # noqa: F401, E402
    turnover_20d,
    amount_20d,
)
from .technical import (  # noqa: F401, E402
    rsi_14d,
    bias_20d,
)
from .williams import (   # noqa: F401, E402
    williams_r_20d,
)
