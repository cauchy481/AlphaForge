"""配置加载模块

优先级（高→低）：
  1. 环境变量 TUSHARE_TOKEN（仅覆盖 tushare.token）
  2. config/settings.local.yaml（整体覆盖，已在 .gitignore 中，本地私有）
  3. config/settings.yaml（版本控制，token 留空）
"""
import os
from pathlib import Path
from typing import Any, Dict
import yaml


def _deep_merge(base: Dict, override: Dict) -> Dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(config_path: str = None) -> Dict[str, Any]:
    """加载配置，支持本地覆盖文件和环境变量。"""
    if config_path is None:
        config_dir = Path(__file__).parent.parent / "config"
        config_path = config_dir / "settings.yaml"
    else:
        config_dir = Path(config_path).parent

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # settings.local.yaml 覆盖（本地私有，不进 git）
    local_path = config_dir / "settings.local.yaml"
    if local_path.exists():
        with open(local_path, "r", encoding="utf-8") as f:
            local = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, local)

    # 环境变量 TUSHARE_TOKEN 最高优先级
    env_token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if env_token:
        cfg.setdefault("tushare", {})["token"] = env_token

    return cfg
