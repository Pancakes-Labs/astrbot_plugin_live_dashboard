"""服务层共享基类。

职责：
- 从插件配置构建并持有统一 :class:`ApiClient`。
- 统一资源释放入口（配合插件 terminate 生命周期）。
- 提供统一 API 异常→用户提示映射 :meth:`_map_api_errors` 与
  基础配置校验 :meth:`_check_base_url`，消除各服务重复的 try/except 样板。
- 各具体服务（实时状态 / 时间线 / 健康 / 好友）继承本基类，
  只关心各自的业务编排与渲染。
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, TypeVar

from astrbot.api import logger

from ..utils.config_parser import get_text_value
from .api_client import (
    ApiClient,
    ApiError,
    AuthenticationError,
    HttpApiError,
    InvalidResponseError,
    NetworkApiError,
    TimeoutApiError,
    make_client_from_config,
)
from .telemetry_utils import track_error_safely

_T = TypeVar("_T")


class BaseService:
    """持有单一 ApiClient 的服务基类。"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        # 惰性创建客户端：仅在第一次业务调用时构建，避免无意义消耗。
        self._client: ApiClient | None = None
        # 遥测管理器引用（由主插件注入）
        self.telemetry: Any | None = None

    def set_telemetry(self, telemetry: Any) -> None:
        """注入或更新遥测管理器引用。"""
        self.telemetry = telemetry

    @property
    def client(self) -> ApiClient:
        """按需构建并缓存 ApiClient。"""
        if self._client is None:
            self._client = make_client_from_config(self.config)
        return self._client

    async def close(self) -> None:
        """释放持有的客户端资源（幂等）。"""
        if self._client is not None:
            await self._client.close()
            self._client = None
        logger.debug("[视奸面板] %s 资源已释放", type(self).__name__)

    def _check_base_url(self) -> str | None:
        """校验服务地址配置，缺失时返回可读提示（供调用方直接返回）。

        Returns:
            配置缺失时的提示文本；配置正常时返回 None。
        """
        if not get_text_value(self.config, "base_url", ""):
            logger.warning("[视奸面板] 配置缺失：服务地址未填写")
            return "未配置 Live Dashboard 地址，请在插件配置中填写 base_url。"
        return None

    async def _map_api_errors(
        self,
        operation: str,
        request: Awaitable[_T],
        *,
        auth_hint: str = "",
    ) -> tuple[_T | None, str | None]:
        """执行一次上游请求并把 ApiClient 异常统一映射为用户可读提示。

        Args:
            operation: 业务动作描述（用于日志，如「状态请求 / 时间线请求」）。
            request: 待 await 的请求协程（由 ApiClient 提供）。
            auth_hint: 鉴权失败时的完整提示文本；为空时使用通用文案。

        Returns:
            (payload, None) 成功；(None, 错误文本) 失败。
            错误文本面向终端用户可读，禁止透传堆栈。
        """
        try:
            payload = await request
        except AuthenticationError as exc:
            logger.warning("[视奸面板] %s 鉴权失败：请检查 auth_token", operation)
            await track_error_safely(
                self.telemetry,
                exc,
                module=f"service.{type(self).__name__}.{operation}",
            )
            return None, auth_hint or "鉴权失败：请检查 auth_token 是否正确。"
        except TimeoutApiError as exc:
            logger.warning("[视奸面板] %s 请求超时：Live Dashboard 响应过慢", operation)
            await track_error_safely(
                self.telemetry,
                exc,
                module=f"service.{type(self).__name__}.{operation}",
            )
            return None, "请求超时：Live Dashboard 响应过慢，请稍后重试。"
        except HttpApiError as exc:
            logger.warning(
                "[视奸面板] %s HTTP 状态异常，状态码：%s", operation, exc.status_code
            )
            await track_error_safely(
                self.telemetry,
                exc,
                module=f"service.{type(self).__name__}.{operation}",
            )
            return None, f"请求失败：服务端返回 HTTP {exc.status_code}。"
        except NetworkApiError as exc:
            logger.warning("[视奸面板] %s 网络请求异常", operation)
            await track_error_safely(
                self.telemetry,
                exc,
                module=f"service.{type(self).__name__}.{operation}",
            )
            return None, "网络错误：无法连接到 Live Dashboard 服务。"
        except InvalidResponseError as exc:
            logger.warning("[视奸面板] %s 上游响应结构异常", operation)
            await track_error_safely(
                self.telemetry,
                exc,
                module=f"service.{type(self).__name__}.{operation}",
            )
            return None, "响应异常：Live Dashboard 返回的数据格式不符合预期。"
        except ApiError as exc:
            logger.warning("[视奸面板] %s API 请求失败：%s", operation, exc)
            await track_error_safely(
                self.telemetry,
                exc,
                module=f"service.{type(self).__name__}.{operation}",
            )
            return None, "请求失败：请查看 AstrBot 日志。"
        except Exception as exc:  # noqa: BLE001
            logger.exception("[视奸面板] %s 未预期异常：%s", operation, exc)
            await track_error_safely(
                self.telemetry,
                exc,
                module=f"service.{type(self).__name__}.{operation}",
            )
            return None, "发生未预期错误：请查看 AstrBot 日志。"
        return payload, None


__all__ = ["BaseService"]
