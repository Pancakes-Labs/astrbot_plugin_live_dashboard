"""实时状态业务编排层。

职责：
- 继承 :class:`BaseService` 复用统一请求客户端与异常映射。
- 拉取 /api/current 并交给渲染层产出回复文本。
- 把 ApiClient 的异常统一映射为可读的用户提示（拒绝透传堆栈）。
"""

from __future__ import annotations

# AstrBot 统一日志对象。
from astrbot.api import logger

from .base_service import BaseService
from .message_renderer import render_dashboard_message_with_count

# 本端点鉴权失败提示的附加说明（与其余端点区分，说明路径占用场景）。
_AUTH_HINT = "鉴权失败：请检查鉴权 Token 是否正确，或确认服务端是否允许访问"


class DashboardService(BaseService):
    """实时状态查询服务（/api/current 的编排）。"""

    async def query_and_render(self) -> tuple[str, int]:
        """拉取并渲染实时状态，返回 (文本, 展示设备数)。"""
        # 地址未配置时直接返回可读提示，避免无意义请求。
        config_error = self._check_base_url()
        if config_error:
            return config_error, 0

        logger.debug("[视奸面板] 开始请求上游状态接口")

        # 统一异常映射：本服务鉴权失败附带端点路径提示，其余文案与各服务一致。
        payload, error = await self._map_api_errors(
            "状态请求", self.client.get_current(), auth_hint=_AUTH_HINT
        )
        if error:
            return error, 0
        assert payload is not None  # error 为 None 时必有 payload

        device_count = (
            len(payload.get("devices", []))
            if isinstance(payload.get("devices"), list)
            else 0
        )
        logger.debug("[视奸面板] 上游请求成功，设备数：%s", device_count)

        rendered_message, render_device_count = render_dashboard_message_with_count(
            payload, self.config
        )

        logger.info(
            "[视奸面板] 文本渲染完成，回复字符数：%s, 展示设备数：%s",
            len(rendered_message),
            render_device_count,
        )
        return rendered_message, render_device_count


__all__ = ["DashboardService"]
