"""健康数据查询业务编排层。

职责：
- 提供按日期查询健康数据并渲染文本的能力。
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
from .api_client import ApiError
from .base_service import BaseService
from .health_renderer import render_health_message


class HealthService(BaseService):
    """健康数据查询服务（/api/health-data 的编排）。"""

    async def query_and_render(
        self,
        date: str | None = None,
        device_id: str | None = None,
    ) -> str:
        """查询并渲染指定日期的健康数据。

        Args:
            date: 形如 YYYY-MM-DD；缺省时使用「今天」。
            device_id: 可选，仅查询指定设备。

        Returns:
            渲染后的文本。
        """
        config_error = self._check_base_url()
        if config_error:
            return config_error

        if date is None:
            date = get_today_str()
        elif not is_valid_date_str(date):
            return f"日期格式不正确：{date}，应为 YYYY-MM-DD 喵。"

        # /api/health-data 的 records 不含 device_name，先并行拉 /api/current
        # 拿 device_id → 设备名映射，供渲染层展示友好名称。失败不阻塞主流程。
        device_names: dict[str, str] = {}
        try:
            current_payload = await self.client.get_current()
            devices_raw = current_payload.get("devices", [])
            if isinstance(devices_raw, list):
                for device_item in devices_raw:
                    if not isinstance(device_item, dict):
                        continue
                    did = device_item.get("device_id")
                    dname = device_item.get("device_name")
                    if did and dname:
                        device_names[str(did)] = str(dname)
        except ApiError:
            logger.debug("[视奸面板] 拉取设备名映射失败，健康渲染回退为使用 device_id")

        payload, error = await self._map_api_errors(
            "健康数据请求",
            self.client.get_health_data(
                date, get_browser_tz_offset_minutes(), device_id
            ),
        )
        if error:
            return error
        assert payload is not None  # error 为 None 时必有 payload

        message = render_health_message(payload, self.config, device_names=device_names)
        logger.info("[视奸面板] 健康数据渲染完成，日期：%s", date)
        return message


__all__ = ["HealthService"]
