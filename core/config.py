"""配置加载模块"""
from pathlib import Path
from typing import Any, Dict
import yaml


def load_config(config_path: str = None) -> Dict[str, Any]:
    """加载 YAML 配置文件，默认读取 config/settings.yaml"""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
