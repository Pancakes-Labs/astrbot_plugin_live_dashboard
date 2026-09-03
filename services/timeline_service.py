"""时间线查询业务编排层。

职责：
- 提供按日期查询时间线并渲染文本的能力。
- 时区语义与上游一致：tz 使用浏览器 getTimezoneOffset 语义（UTC+8 为 -480）。
"""

from __future__ import annotations

# AstrBot 统一日志对象。
from astrbot.api import logger

from ..utils.time_formatter import (
    get_browser_tz_offset_minutes,
    get_today_str,
    is_valid_date_str,
)
from .base_service import BaseService
from .timeline_renderer import render_timeline_message


class TimelineService(BaseService):
    """时间线查询服务（/api/timeline 的编排）。"""

    async def query_and_render(
        self,
        date: str | None = None,
        device_id: str | None = None,
    ) -> tuple[str, int]:
        """查询并渲染指定日期的时间线。

        Args:
            date: 形如 YYYY-MM-DD；缺省时使用「今天」。
            device_id: 可选，仅查询指定设备。

        Returns:
            (渲染文本, 段数)。
        """
        config_error = self._check_base_url()
        if config_error:
            return config_error, 0

        if date is None:
            date = get_today_str()
        elif not is_valid_date_str(date):
            return f"日期格式不正确：{date}，应为 YYYY-MM-DD 喵。", 0

        # 本地时区偏移统一由工具函数提供（与 JS getTimezoneOffset 语义一致）。
        payload, error = await self._map_api_errors(
            "时间线请求",
            self.client.get_timeline(date, get_browser_tz_offset_minutes(), device_id),
        )
        if error:
            return error, 0
        assert payload is not None  # error 为 None 时必有 payload

        message, segment_count = render_timeline_message(payload, self.config)
        logger.info(
            "[视奸面板] 时间线渲染完成，日期：%s，段数：%s", date, segment_count
        )
        return message, segment_count


__all__ = ["TimelineService"]
