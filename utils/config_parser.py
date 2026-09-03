from __future__ import annotations

from typing import Any


def lookup_config_value(config: dict[str, Any], key: str) -> tuple[bool, Any]:
    """按兼容策略查找配置值，适配扁平旧键与嵌套分组两种形态。

    查找优先级（自底向上）：
    1. 点号路径：connection.base_url 精确访问嵌套分组；
    2. 顶层扁平键：旧版 _conf_schema.json 直接保存的键；
    3. 分组内搜索：在顶层 object 分组（手风琴容器）的 items 中查找同名键。

    Returns:
        (是否找到, 值)。未找到时第二个元素恒为 None。
    """
    # 1) 点号路径：按 "a.b.c" 逐层下沉。
    parts = [part for part in key.split(".") if part]
    if len(parts) > 1:
        node: Any = config
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                break
        else:
            return True, node

    # 2) 顶层扁平键（旧版配置文件形态，或 AstrBot 迁移后残留）。
    if key in config:
        return True, config[key]

    # 3) 顶层 object 分组内搜索（新版手风琴容器 items）。
    for group_value in config.values():
        if isinstance(group_value, dict) and key in group_value:
            return True, group_value[key]

    return False, None


def get_text_value(config: dict[str, Any], key: str, default: str = "") -> str:
    """读取字符串配置并去除首尾空白。

    设计目的：
    - 统一处理配置项中的 None、数字、布尔等非字符串输入。
    - 避免调用方重复写 str(...).strip() 的样板代码。
    - 兼容 _conf_schema.json 的扁平旧键与嵌套分组（手风琴）两种形态。
    """
    # 从配置中读取目标键，缺失时使用默认值。
    found, value = lookup_config_value(config, key)
    if not found:
        value = default

    # 对 None 做特殊处理：保持默认值语义，避免把 None 转成字符串 "None"。
    if value is None:
        return default

    # 统一转字符串并去除首尾空白。
    return str(value).strip()


def get_bool_value(config: dict[str, Any], key: str, default: bool = False) -> bool:
    """读取布尔配置，兼容常见字符串写法。

    支持的“真值”字符串：
    - "1" / "true" / "yes" / "on"（大小写不敏感）

    兼容 _conf_schema.json 的扁平旧键与嵌套分组两种形态。
    """
    # 读取原始值（扁平旧键 / 嵌套分组均可命中）。
    found, value = lookup_config_value(config, key)
    if not found:
        value = default

    # 若本身就是 bool，直接返回。
    if isinstance(value, bool):
        return value

    # 字符串按约定真值集合解析。
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}

    # 其他类型（如 int/float/list）回退到 Python 原生 bool 语义。
    return bool(value)


def parse_list_config(raw_text: str, *, to_lower: bool = False) -> list[str]:
    """解析列表型文本配置（支持逗号/分号/换行分隔）。

    Args:
        raw_text: 原始配置文本。
        to_lower: 是否把结果统一转为小写。
    """
    separators = [",", "，", ";", "；", "\n", "\r", "\t"]
    normalized = raw_text
    for separator in separators:
        normalized = normalized.replace(separator, ",")

    values: list[str] = []
    for part in normalized.split(","):
        value = part.strip()
        if not value:
            continue
        values.append(value.lower() if to_lower else value)

    return values


def get_int_value(
    config: dict[str, Any],
    key: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    """读取整数配置，并可选执行上下限裁剪。

    典型用途：
    - 请求超时秒数
    - 最大展示数量
    - 各类阈值参数
    """
    # 先取原始配置值（扁平旧键 / 嵌套分组均可命中），缺失时使用默认值。
    found, value = lookup_config_value(config, key)
    if not found:
        value = default

    # 尝试转换为 int，失败则回退默认值。
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default

    # 若配置了最小值，执行下限保护。
    if min_value is not None:
        number = max(min_value, number)

    # 若配置了最大值，执行上限保护。
    if max_value is not None:
        number = min(max_value, number)

    return number


__all__ = [
    "get_text_value",
    "get_bool_value",
    "get_int_value",
    "parse_list_config",
    "lookup_config_value",
]
