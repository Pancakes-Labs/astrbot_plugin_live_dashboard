"""遥测安全辅助工具。

提供跨模块复用的 best-effort 遥测调用封装，
避免各业务服务重复实现启用检查、异常吞噬与调试日志输出。
"""

from __future__ import annotations

from typing import Any

from astrbot.api import logger


async def track_feature_safely(
    telemetry: Any,
    feature_name: str,
    extra: dict[str, Any] | None = None,
    *,
    log_context: str = "命令与功能行为遥测",
) -> bool:
    """安全上报功能使用匿名行为事件。"""
    if not telemetry or not getattr(telemetry, "enabled", False):
        return False
    try:
        return bool(await telemetry.track_feature(feature_name, extra or {}))
    except Exception as exc:
        logger.debug("[视奸面板] %s 上报失败（已忽略）: %s", log_context, exc)
        return False


async def track_error_safely(
    telemetry: Any,
    exception: Exception,
    *,
    module: str | None = None,
    log_context: str = "错误事件遥测",
) -> bool:
    """安全上报错误事件。"""
    if not telemetry or not getattr(telemetry, "enabled", False):
        return False
    normalized_module = str(module).lower() if module is not None else None
    try:
        return bool(await telemetry.track_error(exception, module=normalized_module))
    except Exception as exc:
        logger.debug("[视奸面板] %s 上报失败（已忽略）: %s", log_context, exc)
        return False


__all__ = ["track_feature_safely", "track_error_safely"]
