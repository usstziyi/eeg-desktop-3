import json
import os
from copy import deepcopy
from typing import Any

_DEFAULT_CONFIG = {
    "device": {
        "name": "synthetic",
        "serial_port": ""
    },
    "display": {
        "refresh_ms": 50,
        "window_seconds": 6.0,
        "amplitude_range": 10
    },
    "process": {
        "detrend": True,
        "bp_low_hz": 0.1,
        "bp_high_hz": 45.0,
        "notch_hz": 50.0
    },
    "spectrum": {
        "window_type": "Hann",
        "spectrum_window": 4.0,
        "overlap_ratio": 50
    },
    "recording": {
        "record_original": False,
        "record_processed": False
    }
}


class Settings:
    def __init__(self):
        self._data = deepcopy(_DEFAULT_CONFIG)
        self._filepath: str | None = None

    @property
    def data(self) -> dict:
        return self._data

    def load(self, filepath: str) -> None:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # 用于 递归地将 JSON 文件加载的配置合并到现有配置中
            self._merge(self._data, loaded)
        self._filepath = filepath

    def save(self, filepath: str | None = None) -> None:
        target = filepath or self._filepath
        if target is None:
            return
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, *keys: str, default: Any = None) -> Any:
        node = self._data
        for key in keys:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                return default
        return node if node is not None else default

    def set(self, value: Any, *keys: str) -> None:
        # 获取配置数据的根节点
        node = self._data
        # 遍历除最后一个键以外的所有键，逐层创建嵌套字典
        for key in keys[:-1]:
            # 如果键不存在则创建空字典，确保路径存在
            node = node.setdefault(key, {})
        # 在最终节点上设置值
        node[keys[-1]] = value

    @staticmethod
    def _merge(base: dict, overlay: dict) -> None:
        for key, val in overlay.items():
            if isinstance(val, dict) and isinstance(base.get(key), dict):
                Settings._merge(base[key], val)
            else:
                base[key] = val

"""
_DEFAULT_CONFIG (代码硬编码)
        ↓ merge
default_settings.json (可分发)
        ↓ merge
user_settings.json (用户私有，可选)
        ↓
     最终配置
"""
def load_default_settings() -> Settings:
    settings = Settings()
    default_path = os.path.join(os.path.dirname(__file__), "default_settings.json")
    user_path = os.path.join(os.path.dirname(__file__), "user_settings.json")
    settings.load(default_path)
    if os.path.exists(user_path):
        settings.load(user_path)
    return settings
