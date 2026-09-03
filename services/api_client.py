"""统一 HTTP 请求客户端层。

职责：
- 封装对上游 Live Dashboard 各只读 API 的请求（GET）。
- 把 httpx 异常统一转换为插件自定义异常，供各服务层映射为用户提示。
- 避免各服务重复编写 URL 拼接、请求头、异常兜底逻辑（DRY）。

设计约定：
- 所有请求均为只读 GET，附带可选 Bearer 鉴权。
- 响应必须是 JSON 对象，否则视为无效响应。
- 销毁资源统一走 close()。
"""

from __future__ import annotations

from typing import Any

import httpx

# AstrBot 统一日志对象，用于记录请求链路关键信息。
from astrbot.api import logger

from ..utils.config_parser import get_int_value, get_text_value


class ApiError(Exception):
    """API 请求失败基类，所有派生异常均可被上层捕获。"""


class HttpApiError(ApiError):
    """服务端返回非 2xx 状态。"""

    def __init__(self, status_code: int, path: str) -> None:
        self.status_code = status_code
        self.path = path
        super().__init__(f"HTTP {status_code} @ {path}")


class AuthenticationError(HttpApiError):
    """401/403：鉴权失败。"""


class TimeoutApiError(ApiError):
    """请求超时。"""


class NetworkApiError(ApiError):
    """网络层错误（DNS、连接失败、证书等）。"""


class InvalidResponseError(ApiError):
    """响应非 JSON 对象或结构异常。"""


class ApiClient:
    """面向单个 Live Dashboard 实例的只读客户端。"""

    def __init__(
        self,
        base_url: str,
        auth_token: str = "",
        timeout_sec: int = 30,
    ) -> None:
        """初始化客户端。

        Args:
            base_url: 面板根地址（不含尾部斜杠与 /api 路径）。
            auth_token: 可选 Bearer Token，空串表示不启用鉴权。
            timeout_sec: 请求超时（秒）。
        """
        # 去除尾斜杠，避免拼出 //api/current。
        self.base_url = base_url.rstrip("/")
        self._timeout_sec = timeout_sec
        self._client = httpx.AsyncClient(timeout=timeout_sec)
        self._headers: dict[str, str] = {"Accept": "application/json"}
        if auth_token:
            self._headers["Authorization"] = f"Bearer {auth_token}"

    async def close(self) -> None:
        """释放底层 HTTP 连接池。"""
        await self._client.aclose()

    async def _get_json(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """执行 GET 请求并返回 JSON 对象。

        失败时抛出 :class:`ApiError` 子类，由上层映射为用户提示。
        """
        url = f"{self.base_url}{path}"
        logger.debug(
            "[视奸面板] 请求 %s，参数：%s，鉴权：%s",
            url,
            params or {},
            "开启" if "Authorization" in self._headers else "关闭",
        )

        try:
            response = await self._client.get(url, headers=self._headers, params=params)
        except httpx.TimeoutException as exc:
            logger.warning("[视奸面板] 请求超时：%s", url)
            raise TimeoutApiError(f"请求超时：{url}") from exc
        except httpx.RequestError as exc:
            logger.warning("[视奸面板] 网络请求异常：%s", exc)
            raise NetworkApiError(f"网络错误：{url}") from exc

        # 鉴权与权限类错误单独归类，便于上层给出针对性提示。
        if response.status_code in (401, 403):
            logger.warning(
                "[视奸面板] 鉴权失败，状态码：%s，路径：%s", response.status_code, path
            )
            raise AuthenticationError(response.status_code, path)

        if response.status_code >= 400:
            logger.warning(
                "[视奸面板] HTTP 状态异常，状态码：%s，路径：%s",
                response.status_code,
                path,
            )
            raise HttpApiError(response.status_code, path)

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("[视奸面板] 响应体不是合法 JSON：%s", path)
            raise InvalidResponseError(f"响应不是合法 JSON：{path}") from exc

        # 防御式校验：要求最外层必须是对象，便于后续按键访问。
        if not isinstance(data, dict):
            logger.error("[视奸面板] 响应结构异常：响应体不是 JSON 对象：%s", path)
            raise InvalidResponseError(f"响应不是 JSON 对象：{path}")

        return data

    async def get_current(self) -> dict[str, Any]:
        """拉取 /api/current 实时状态。"""
        return await self._get_json("/api/current")

    async def get_timeline(
        self, date: str, tz_offset_minutes: int, device_id: str | None = None
    ) -> dict[str, Any]:
        """拉取 /api/timeline 时间线。

        Args:
            date: 形如 YYYY-MM-DD 的本地日期。
            tz_offset_minutes: 浏览器时区偏移（UTC+8 为 -480），与上游语义一致。
            device_id: 可选，仅查询指定设备。
        """
        params: dict[str, Any] = {"date": date, "tz": str(tz_offset_minutes)}
        if device_id:
            params["device_id"] = device_id
        return await self._get_json("/api/timeline", params)

    async def get_health_data(
        self, date: str, tz_offset_minutes: int, device_id: str | None = None
    ) -> dict[str, Any]:
        """拉取 /api/health-data 健康数据。

        Args:
            date: 形如 YYYY-MM-DD 的本地日期。
            tz_offset_minutes: 浏览器时区偏移（UTC+8 为 -480），与上游语义一致。
            device_id: 可选，仅查询指定设备。
        """
        params: dict[str, Any] = {"date": date, "tz": str(tz_offset_minutes)}
        if device_id:
            params["device_id"] = device_id
        return await self._get_json("/api/health-data", params)

    async def get_config(self) -> dict[str, Any]:
        """拉取 /api/config 站点配置（面板显示名、好友面板等）。"""
        return await self._get_json("/api/config")

    async def get_health(self) -> dict[str, Any]:
        """拉取 /api/health 服务健康检查（status/uptime/timestamp）。"""
        return await self._get_json("/api/health")

    async def get_proxy_current(self, dashboard_id: str) -> dict[str, Any]:
        """通过只读代理拉取指定好友面板的 /api/current。

        Args:
            dashboard_id: 好友面板在 /api/config 中的 id。
        """
        params: dict[str, str] = {"dashboard_id": dashboard_id, "endpoint": "current"}
        return await self._get_json("/api/proxy", params)

    async def get_proxy_timeline(
        self,
        dashboard_id: str,
        date: str,
        tz_offset_minutes: int,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        """通过只读代理拉取指定好友面板的 /api/timeline。

        Args:
            dashboard_id: 好友面板 id。
            date: 形如 YYYY-MM-DD 的本地日期。
            tz_offset_minutes: 浏览器时区偏移（UTC+8 为 -480）。
            device_id: 可选，仅查询指定设备。
        """
        params: dict[str, str] = {
            "dashboard_id": dashboard_id,
            "endpoint": "timeline",
            "date": date,
            "tz": str(tz_offset_minutes),
        }
        if device_id:
            params["device_id"] = device_id
        return await self._get_json("/api/proxy", params)

    async def get_proxy_health_data(
        self,
        dashboard_id: str,
        date: str,
        tz_offset_minutes: int,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        """通过只读代理拉取指定好友面板的 /api/health-data。

        Args:
            dashboard_id: 好友面板 id。
            date: 形如 YYYY-MM-DD 的本地日期。
            tz_offset_minutes: 浏览器时区偏移（UTC+8 为 -480）。
            device_id: 可选，仅查询指定设备。
        """
        params: dict[str, str] = {
            "dashboard_id": dashboard_id,
            "endpoint": "health-data",
            "date": date,
            "tz": str(tz_offset_minutes),
        }
        if device_id:
            params["device_id"] = device_id
        return await self._get_json("/api/proxy", params)

    async def get_proxy_config(self, dashboard_id: str) -> dict[str, Any]:
        """通过只读代理拉取指定好友面板的 /api/config。

        Args:
            dashboard_id: 好友面板在 /api/config 中的 id。
        """
        params: dict[str, str] = {"dashboard_id": dashboard_id, "endpoint": "config"}
        return await self._get_json("/api/proxy", params)


def make_client_from_config(config: dict[str, Any]) -> ApiClient:
    """从插件配置构建 ApiClient。

    统一在这里读取 base_url / auth_token / request_timeout_sec，
    避免各服务重复实现配置读取逻辑。
    """
    base_url = get_text_value(config, "base_url", "")
    auth_token = get_text_value(config, "auth_token", "")
    timeout_sec = get_int_value(
        config, "request_timeout_sec", 30, min_value=1, max_value=600
    )
    return ApiClient(base_url=base_url, auth_token=auth_token, timeout_sec=timeout_sec)


__all__ = [
    "ApiClient",
    "ApiError",
    "AuthenticationError",
    "HttpApiError",
    "InvalidResponseError",
    "NetworkApiError",
    "TimeoutApiError",
    "make_client_from_config",
]
