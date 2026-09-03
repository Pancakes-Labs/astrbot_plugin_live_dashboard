"""服务健康检查业务编排层。

职责：
- 拉取上游 /api/health 健康检查端点（status/uptime/timestamp）。
- 供「视奸服务状态」指令展示服务连通性与运行时长，方便排障。
"""

from __future__ import annotations

from ..utils.time_formatter import format_time_text
from .base_service import BaseService


class SystemStatusService(BaseService):
    """服务健康状态查询（/api/health 的编排）。"""

    async def query_and_render(self) -> str:
        """拉取并渲染服务健康状态文本。"""
        config_error = self._check_base_url()
        if config_error:
            return config_error

        payload, error = await self._map_api_errors(
            "服务状态请求", self.client.get_health()
        )
        if error:
            return error
        assert payload is not None  # error 为 None 时必有 payload

        status = payload.get("status", "unknown")
        uptime_sec = payload.get("uptime")
        timestamp = payload.get("timestamp", "")

        lines = ["💚 Live Dashboard 服务状态"]
        if isinstance(uptime_sec, (int, float)):
            lines.append(f"状态：{'正常' if status == 'ok' else status}")
            lines.append(f"运行时长：{_format_uptime(int(uptime_sec))}")
        else:
            lines.append(f"状态：{status or 'unknown'}")
        if isinstance(timestamp, str) and timestamp.strip():
            lines.append(f"服务端时间：{format_time_text(timestamp)}")
        return "\n".join(lines)


def _format_uptime(total_sec: int) -> str:
    """把秒数格式化为「N天N小时N分N秒」。"""
    days, rem = divmod(max(0, total_sec), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if minutes:
        parts.append(f"{minutes}分")
    if not parts or seconds:
        parts.append(f"{seconds}秒")
    return "".join(parts)


__all__ = ["SystemStatusService", "_format_uptime"]
