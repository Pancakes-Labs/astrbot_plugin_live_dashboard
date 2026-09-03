"""通用文本处理工具（纯逻辑，无 IO）。

集中存放多个渲染层重复实现的纯文本工具函数（安全转字符串、敏感词打码、
短时间截取），消除 DRY 违反；同时提供统一的 NSFW 打码文案常量。
"""

from __future__ import annotations

from typing import Any

from .time_formatter import format_time_text

# NSFW 命中时的统一打码文案（与各渲染层保持一致）。
NSFW_MASK_TEXT = "（内容已隐藏喵~）"


def clean_text(value: Any) -> str:
    """安全转字符串并去除首尾空白。"""
    if value is None:
        return ""
    return str(value).strip()


def mask_sensitive_text(text: str, keywords: list[str], replacement: str) -> str:
    """命中敏感关键词时整体替换。"""
    if not text or not keywords:
        return text
    if any(keyword in text.lower() for keyword in keywords):
        return replacement
    return text


def format_short_time(raw_time: str) -> str:
    """把 ISO 时间格式化为短时间（HH:MM）。

    基于 :func:`format_time_text` 的 "MM-DD HH:MM:SS" 输出，截取时分部分；
    解析失败时由 time_formatter 回退原文。
    """
    formatted = format_time_text(raw_time)
    if " " in formatted:
        return formatted.split(" ")[1][:5]
    return formatted


__all__ = ["NSFW_MASK_TEXT", "clean_text", "format_short_time", "mask_sensitive_text"]
