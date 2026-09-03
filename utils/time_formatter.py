"""时间与日期工具（纯逻辑，无 IO）。

集中存放时间格式化、日期校验与浏览器风格时区偏移计算。
"""

from __future__ import annotations

import re
from datetime import datetime

# YYYY-MM-DD 严格格式（供服务层日期校验复用）。
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def format_time_text(raw_text: str) -> str:
    """将 ISO 时间字符串格式化为本地可读文本。

    输入示例：
    - "2026-03-24T12:00:05.000Z"
    - "2026-03-24T12:00:05+00:00"

    输出格式：
    - "03-24 20:00:05"（按当前系统本地时区显示）
    """
    try:
        # 兼容常见 Zulu 时间写法：把尾部 "Z" 转为 "+00:00"。
        dt = datetime.fromisoformat(raw_text.replace("Z", "+00:00"))

        # 转换到本地时区并格式化为“月-日 时:分:秒”。
        return dt.astimezone().strftime("%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        # 解析失败时回退原文，避免因为时间格式异常导致整条消息渲染失败。
        return raw_text


def format_relative_time(raw_text: str) -> str:
    """将 ISO 时间字符串格式化为相对时间描述。

    规则（基于本地时区当前时刻）：
    - 不足 10 秒显示「刚刚」；
    - 不足 1 分钟显示「N秒前」；
    - 不足 1 小时显示「N分钟前」；
    - 当天内不足 24 小时显示「N小时前」；
    - 其余回退为紧凑时间「MM-DD HH:MM」。

    解析失败时返回空字符串（由调用方决定是否回退展示）。
    """
    try:
        dt = datetime.fromisoformat(raw_text.replace("Z", "+00:00")).astimezone()
    except Exception:  # noqa: BLE001
        return ""
    now = datetime.now().astimezone()
    diff_sec = max(0, int((now - dt).total_seconds()))
    if diff_sec < 10:
        return "刚刚"
    if diff_sec < 60:
        return f"{diff_sec}秒前"
    if diff_sec < 3600:
        return f"{diff_sec // 60}分钟前"
    if diff_sec < 86400 and now.date() == dt.date():
        return f"{diff_sec // 3600}小时前"
    return dt.strftime("%m-%d %H:%M")


def is_valid_date_str(value: str) -> bool:
    """判断字符串是否为合法 YYYY-MM-DD 日期格式。"""
    return bool(_DATE_PATTERN.match(value))


def get_today_str() -> str:
    """返回本地时区的今天日期（YYYY-MM-DD）。"""
    return datetime.now().strftime("%Y-%m-%d")


def get_browser_tz_offset_minutes() -> int:
    """返回当前本地时区的浏览器风格偏移（UTC+8 为 -480）。

    与上游 JS getTimezoneOffset 语义一致：东时区为负、西时区为正。
    utcoffset() 恒为整分钟，因此直接截断不会引入精度误差。
    """
    return int(-datetime.now().astimezone().utcoffset().total_seconds() / 60)


__all__ = [
    "format_relative_time",
    "format_time_text",
    "get_browser_tz_offset_minutes",
    "get_today_str",
    "is_valid_date_str",
]
