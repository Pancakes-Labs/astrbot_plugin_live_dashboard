"""好友面板（多面板聚合）业务编排层。

职责：
- 读取上游 /api/config 拉取的 dashboards 列表（EXTERNAL_DASHBOARDS 配置的聚合面板）。
- 支持按名称列出所有好友面板，或按名称/id 查询某个好友面板的实时状态。
- 通过上游只读代理 /api/proxy 访问，避免直连好友原面板。
- config 拉取带短时 TTL 缓存，避免高频查询下重复请求上游。
"""

from __future__ import annotations

import time
from typing import Any

# AstrBot 统一日志对象。
from astrbot.api import logger

from ..utils.config_parser import get_int_value
from ..utils.time_formatter import get_browser_tz_offset_minutes, get_today_str
from .base_service import BaseService
from .health_renderer import render_health_message
from .message_renderer import render_dashboard_message_with_count
from .timeline_renderer import render_timeline_message

# 面板缺少 id 字段时无法代理查询的统一提示。
_MISSING_ID_TEXT = "该面板缺少 id 字段，无法查询喵。"


class FriendService(BaseService):
    """好友面板查询服务（基于 /api/config 与 /api/proxy 的编排）。"""

    async def list_friends(self) -> tuple[list[dict[str, Any]], str | None]:
        """拉取可用的好友面板列表（带短时 TTL 缓存）。

        Returns:
            (面板列表, 错误文本)。错误为非 None 时列表为空。
            缓存仅缓存成功结果；TTL 为 0 时禁用缓存。
        """
        config_error = self._check_base_url()
        if config_error:
            return [], config_error

        ttl_sec = get_int_value(
            self.config, "friend_config_cache_ttl_sec", 30, min_value=0, max_value=3600
        )
        cached = getattr(self, "_dashboards_cache", None)
        if ttl_sec > 0 and cached is not None:
            cached_at, cached_list = cached
            if time.monotonic() - cached_at < ttl_sec:
                logger.debug("[视奸面板] 命中好友面板列表缓存")
                return cached_list, None

        config_payload, error = await self._map_api_errors(
            "config 请求", self.client.get_config()
        )
        if error:
            return [], error
        assert config_payload is not None  # error 为 None 时必有 payload

        dashboards_raw = config_payload.get("dashboards", [])
        dashboards = (
            [d for d in dashboards_raw if isinstance(d, dict)]
            if isinstance(dashboards_raw, list)
            else []
        )
        if ttl_sec > 0:
            self._dashboards_cache = (time.monotonic(), dashboards)
        return dashboards, None

    def _find_dashboard(
        self, dashboards: list[dict[str, Any]], name: str
    ) -> dict[str, Any] | None:
        """按名称或 id 模糊匹配面板。"""
        lowered = name.lower()
        for dashboard in dashboards:
            candidate_id = str(dashboard.get("id", "")).lower()
            candidate_name = str(dashboard.get("name", "")).lower()
            if lowered in candidate_id or lowered in candidate_name:
                return dashboard
        return None

    async def _resolve_dashboard(
        self, name: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        """解析名称/id 到面板对象，复用列表与匹配逻辑。

        Returns:
            (面板, 错误文本)；错误为非 None 时面板为 None。
        """
        dashboards, error = await self.list_friends()
        if error:
            return None, error
        if not dashboards:
            return None, "当前未配置任何好友面板喵"

        target = self._find_dashboard(dashboards, name)
        if not target:
            names = "、".join(str(d.get("name", "?")) for d in dashboards)
            return None, f"没有找到名为「{name}」的面板喵。当前可用：{names}"
        return target, None

    @staticmethod
    def _resolve_dashboard_id(target: dict[str, Any]) -> str | None:
        """解析面板可代理查询的 dashboard_id；缺失时返回 None。"""
        return str(target.get("id") or "").strip() or None

    async def query_friend_status(self, name: str) -> tuple[str, bool]:
        """按名称（或 id）查询某个好友面板的实时状态。

        Args:
            name: 面板名称或 id（不区分大小写，子串匹配）。

        Returns:
            (渲染文本, 是否成功)。失败时第二项为 False。
        """
        target, error = await self._resolve_dashboard(name)
        if error:
            return error, False
        assert target is not None  # error 为 None 时必有面板

        dashboard_id = self._resolve_dashboard_id(target)
        if not dashboard_id:
            return _MISSING_ID_TEXT, False

        payload, error = await self._map_api_errors(
            "好友面板请求", self.client.get_proxy_current(dashboard_id)
        )
        if error:
            return error, False
        assert payload is not None

        # 复用状态面板渲染逻辑，标题冠以好友名。
        rendered, _ = render_dashboard_message_with_count(payload, self.config)
        display_name = str(target.get("name") or dashboard_id)
        return f"👥 好友面板「{display_name}」状态\n\n{rendered}", True

    async def query_friend_timeline(
        self, name: str, date: str | None = None, device_id: str | None = None
    ) -> tuple[str, bool]:
        """查询某好友面板指定日期的时间线（经只读代理）。

        Args:
            name: 面板名称或 id。
            date: YYYY-MM-DD，缺省为今天。
            device_id: 可选设备过滤。

        Returns:
            (渲染文本, 是否成功)。
        """
        target, error = await self._resolve_dashboard(name)
        if error:
            return error, False
        assert target is not None

        dashboard_id = self._resolve_dashboard_id(target)
        if not dashboard_id:
            return _MISSING_ID_TEXT, False

        if date is None:
            date = get_today_str()

        payload, error = await self._map_api_errors(
            "好友时间线请求",
            self.client.get_proxy_timeline(
                dashboard_id, date, get_browser_tz_offset_minutes(), device_id
            ),
        )
        if error:
            return error, False
        assert payload is not None

        rendered, _ = render_timeline_message(payload, self.config)
        display_name = str(target.get("name") or dashboard_id)
        return f"👥 好友面板「{display_name}」时间线（{date}）\n\n{rendered}", True

    async def query_friend_health(
        self, name: str, date: str | None = None
    ) -> tuple[str, bool]:
        """查询某好友面板指定日期的健康数据（经只读代理）。

        Args:
            name: 面板名称或 id。
            date: YYYY-MM-DD，缺省为今天。

        Returns:
            (渲染文本, 是否成功)。
        """
        target, error = await self._resolve_dashboard(name)
        if error:
            return error, False
        assert target is not None

        dashboard_id = self._resolve_dashboard_id(target)
        if not dashboard_id:
            return _MISSING_ID_TEXT, False

        if date is None:
            date = get_today_str()

        payload, error = await self._map_api_errors(
            "好友健康数据请求",
            self.client.get_proxy_health_data(
                dashboard_id, date, get_browser_tz_offset_minutes()
            ),
        )
        if error:
            return error, False
        assert payload is not None

        rendered = render_health_message(payload, self.config)
        display_name = str(target.get("name") or dashboard_id)
        return f"👥 好友面板「{display_name}」健康数据（{date}）\n\n{rendered}", True

    async def query_friend_config(self, name: str) -> tuple[str, bool]:
        """查询某好友面板的站点配置信息（经只读代理）。

        Args:
            name: 面板名称或 id。

        Returns:
            (渲染文本, 是否成功)。
        """
        target, error = await self._resolve_dashboard(name)
        if error:
            return error, False
        assert target is not None

        dashboard_id = self._resolve_dashboard_id(target)
        if not dashboard_id:
            return _MISSING_ID_TEXT, False

        payload, error = await self._map_api_errors(
            "好友配置请求", self.client.get_proxy_config(dashboard_id)
        )
        if error:
            return error, False
        assert payload is not None

        display_name = str(
            payload.get("displayName") or target.get("name") or dashboard_id
        )
        site_title = str(payload.get("siteTitle") or "")
        site_desc = str(payload.get("siteDescription") or "")
        lines = [f"🛠 好友面板「{display_name}」配置"]
        if site_title:
            lines.append(f"标题：{site_title}")
        if site_desc:
            lines.append(f"描述：{site_desc}")
        if not site_title and not site_desc:
            lines.append("该面板未提供额外描述信息喵")
        return "\n".join(lines), True


__all__ = ["FriendService"]
