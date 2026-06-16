"""因子注册"""
from typing import Any, Callable, Dict, List, Optional
import inspect
import pandas as pd

class FactorRegistry:


    _factors: Dict[str, dict] = {}

    @classmethod
    def register(
        cls,
        name: str,
        category: str,
        description: str = "",
        params: Optional[dict] = None,
        required_data: Optional[List[str]] = None,
        lookback_days: int = 0,
    ):
        """将因子函数注册到因子库"""
        def decorator(func: Callable):
            cls._factors[name] = {
                "name": name,
                "category": category,
                "description": description,
                "params": params or {},
                "required_data": required_data or [],
                "lookback_days": lookback_days,
                "func": func,
            }
            return func
        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[dict]:
        """按名称获取因子"""
        return cls._factors.get(name)

    @classmethod
    def list_by_category(cls, category: str) -> List[dict]:
        """按分类列出因子"""
        return [v for v in cls._factors.values() if v["category"] == category]

    @classmethod
    def list_all(cls) -> List[dict]:
        """列出所有已注册因子"""
        return list(cls._factors.values())

    @classmethod
    def categories(cls) -> List[str]:
        """列出所有因子分类"""
        return sorted(set(v["category"] for v in cls._factors.values()))

    @classmethod
    def compute(cls, name: str, data, date: str, **kwargs) -> "pd.Series":
        """计算指定因子的值"""
        import pandas as pd
        factor = cls.get(name)
        if factor is None:
            raise ValueError(f"Factor '{name}' not registered")
        params = {**factor["params"], **kwargs}
        result = factor["func"](data, date, **params)
        if isinstance(result, pd.DataFrame):
            if "factor_value" in result.columns:
                result = result.set_index("code")["factor_value"]
            elif result.shape[1] == 1:
                result = result.iloc[:, 0]
        return result
