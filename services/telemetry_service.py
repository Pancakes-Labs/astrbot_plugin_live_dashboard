"""遥测服务主入口。

承载匿名遥测事件发送、配置快照上报与错误脱敏上报能力。

数据脱敏与隐私保护说明:
- 严格遵循隐私优先原则，不收集任何用户隐私信息（如 QQ 号、群号、会话 ID、IP 地址等）。
- 绝对不收集任何设备名、前台应用名、窗口标题、个人活动记录、好友面板名等业务载荷数据。
- 配置快照仅收集功能开关状态与统计性配置，已严格剥离 auth_token、敏感黑名单等凭据。
- 错误堆栈与消息自动剥离本地系统路径与用户名，仅上报错误类型与相对模块。
"""

from __future__ import annotations

import asyncio
import base64
import copy
import platform
import re
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

import aiohttp

from astrbot.api import logger
from astrbot.api.star import StarTools

from ..utils.config_parser import lookup_config_value
from ..utils.version import get_astrbot_version_info


class TelemetryManager:
    """匿名遥测管理器。

    负责异步批量发送匿名遥测数据，并集中管理实例标识、严格脱敏与上报策略。
    """

    # 统一接收遥测的云端接入服务端点
    _ENDPOINT = "https://plugincenter.aloys23.link/api/ingest"
    # 项目标识 slug 与 App Key（Base64 编码增加源码探测复杂度）
    _PROJECT_SLUG = "15fe0b48-0b98-424c-adfe-23155063ae14"
    _ENCODED_KEY = "dGtfb01pNlhlaVJOQk4yUzlkdjRMSWZtUktVZUNLazRRT3I="
    _APP_KEY = base64.b64decode(_ENCODED_KEY).decode()

    # 特定高频事件的最小加入队列间隔（秒），用于在内存中提前丢弃同质化冗余遥测
    _THROTTLE_CONFIG = {
        "feature:command_status": 5.0,
        "feature:command_timeline": 5.0,
        "feature:command_health": 5.0,
        "feature:command_system_status": 5.0,
        "feature:command_friend": 5.0,
        "feature:llm_tool_status": 5.0,
        "feature:llm_tool_timeline": 5.0,
        "feature:llm_tool_health": 5.0,
        "feature:llm_tool_friend": 5.0,
    }

    # 错误事件按"模块 + 异常类型"维度聚合节流的最小间隔（秒），防止瞬时故障刷屏
    _ERROR_THROTTLE_SECONDS = 60.0

    # 物理网络请求的最小时间间隔（秒），防范极端并发下的 429
    _MIN_REQUEST_INTERVAL = 10.0

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        plugin_version: str = "unknown",
    ) -> None:
        """初始化遥测管理器。

        Args:
            config: 插件配置对象
            plugin_version: 插件版本号
        """
        self._config = config or {}
        self._plugin_version = plugin_version

        # 获取 AstrBot 版本号与探测来源
        self._astrbot_version_info = get_astrbot_version_info()
        self._astrbot_version = self._astrbot_version_info.version

        # 从配置中读取遥测开关（兼容嵌套与扁平配置）
        _, telemetry_val = lookup_config_value(self._config, "telemetry_config.enabled")
        if telemetry_val is None:
            _, telemetry_val = lookup_config_value(self._config, "telemetry_enabled")
        self._enabled = True if telemetry_val is None else bool(telemetry_val)

        # 获取或创建持久化实例 ID
        self._instance_id = self._get_or_create_instance_id()

        # aiohttp session 延迟初始化
        self._session: aiohttp.ClientSession | None = None
        self._env = "production"

        # 缓冲队列与调度锁
        self._queue: list[dict[str, Any]] = []
        self._queue_lock = asyncio.Lock()
        self._send_task: asyncio.Task[None] | None = None
        self._last_429_time: datetime | None = None

        # 后台批处理循环唤醒事件
        self._wake_event = asyncio.Event()

        # 在途发送标志
        self._sending = False

        # 事件节流时间记录表
        self._last_throttled_times: dict[str, float] = {}

        # 物理请求速率限制与互斥锁
        self._last_send_time: float = 0.0
        self._send_semaphore = asyncio.Semaphore(1)

        # 关闭状态标志
        self._closed = False

        if self._enabled:
            logger.debug(
                "[视奸面板] 已启用匿名遥测，实例标识为 %s，AstrBot 版本为 %s",
                self._instance_id,
                self._astrbot_version,
            )
        else:
            logger.debug("[视奸面板] 匿名遥测功能未启用")

    def _get_or_create_instance_id(self) -> str:
        """获取或创建实例标识，并持久化到插件数据目录。"""
        try:
            data_dir = StarTools.get_data_dir("astrbot_plugin_live_dashboard")
            id_file = data_dir / ".telemetry_id"

            if id_file.exists():
                instance_id = id_file.read_text(encoding="utf-8").strip()
                if instance_id:
                    return instance_id

            instance_id = str(uuid.uuid4())
            data_dir.mkdir(parents=True, exist_ok=True)
            id_file.write_text(instance_id, encoding="utf-8")
            logger.debug("[视奸面板] 已生成新的遥测实例 ID: %s", instance_id)
            return instance_id
        except Exception as exc:
            logger.warning("[视奸面板] 无法持久化遥测实例 ID: %s", exc)
            return str(uuid.uuid4())

    @property
    def enabled(self) -> bool:
        """返回当前是否启用遥测。"""
        return self._enabled

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建内部网络会话。"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def track(
        self,
        event_name: str,
        data: dict[str, Any] | None = None,
        immediate: bool = False,
        bypass_rate_limit: bool = False,
    ) -> bool:
        """发送遥测事件。

        Args:
            event_name: 事件名称
            data: 附加数据对象
            immediate: 是否立即发送，不经过缓冲队列
            bypass_rate_limit: 是否绕过物理发送最小间隔
        """
        if not self._enabled or self._closed:
            return False

        # 内存节流过滤
        throttle_key = event_name
        if event_name == "feature" and data and "feature" in data:
            feature_name = data["feature"]
            action = data.get("action")
            throttle_key = (
                f"feature:{feature_name}:{action}"
                if action
                else f"feature:{feature_name}"
            )
        elif event_name == "error" and data:
            throttle_key = f"error:{data.get('module') or 'unknown'}:{data.get('type') or 'unknown'}"

        throttle_seconds = self._THROTTLE_CONFIG.get(throttle_key)
        if throttle_seconds is None and throttle_key.startswith("feature:"):
            base_key = throttle_key.rsplit(":", 1)[0]
            throttle_seconds = self._THROTTLE_CONFIG.get(base_key)
        if throttle_seconds is None and throttle_key.startswith("error:"):
            throttle_seconds = self._ERROR_THROTTLE_SECONDS

        if throttle_seconds is not None:
            now_ts = time.time()
            last_ts = self._last_throttled_times.get(throttle_key, 0.0)
            if now_ts - last_ts < throttle_seconds:
                return True
            self._last_throttled_times[throttle_key] = now_ts

        # 延迟启动后台批处理任务
        if self._send_task is None or self._send_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._send_task = loop.create_task(self._batch_sender_loop())
            except RuntimeError:
                pass

        event_item = {
            "event": event_name,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if immediate:
            return await self._send_batch_raw(
                [event_item], bypass_rate_limit=bypass_rate_limit
            )

        async with self._queue_lock:
            if self._closed:
                return False
            self._queue.append(event_item)
            should_flush = len(self._queue) >= 50

        if should_flush:
            asyncio.create_task(self.flush())

        return True

    async def _batch_sender_loop(self) -> None:
        """后台批处理发送循环。"""
        while self._enabled and not self._closed:
            try:
                try:
                    await asyncio.wait_for(self._wake_event.wait(), timeout=15.0)
                    self._wake_event.clear()
                except asyncio.TimeoutError:
                    pass
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("[视奸面板] 遥测后台批处理循环异常: %s", exc)

    async def flush(
        self,
        bypass_rate_limit: bool = False,
        *,
        _allow_after_close: bool = False,
    ) -> bool:
        """立即清空缓冲区并批量发送所有缓存的事件。"""
        if not self._enabled or (self._closed and not _allow_after_close):
            return False

        async with self._queue_lock:
            if self._closed and not _allow_after_close:
                return False
            if not self._queue:
                return False
            batch_data = list(self._queue)
            self._queue.clear()

        self._sending = True
        try:
            return await self._send_batch_raw(
                batch_data,
                bypass_rate_limit=bypass_rate_limit,
                _allow_after_close=_allow_after_close,
            )
        finally:
            self._sending = False

    async def _send_batch_raw(
        self,
        batch_data: list[dict[str, Any]],
        *,
        bypass_rate_limit: bool = False,
        _allow_after_close: bool = False,
    ) -> bool:
        """底层实际网络上报接口，包含强制发送速率限制。"""
        payload = {
            "instance_id": self._instance_id,
            "version": self._plugin_version,
            "env": self._env,
            "batch": batch_data,
        }

        async with self._send_semaphore:
            now_ts = time.time()
            elapsed = now_ts - self._last_send_time
            if not bypass_rate_limit and elapsed < self._MIN_REQUEST_INTERVAL:
                wait_time = self._MIN_REQUEST_INTERVAL - elapsed
                await asyncio.sleep(wait_time)

            if self._closed and not (_allow_after_close or self._sending):
                return False

            self._last_send_time = time.time()

            try:
                session = await self._get_session()
                headers = {
                    "Content-Type": "application/json",
                    "X-App-Key": self._APP_KEY,
                }

                async with session.post(
                    self._ENDPOINT,
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        return True
                    if response.status == 401:
                        logger.warning("[视奸面板] 遥测 App Key 无效或项目已禁用")
                    elif response.status == 429:
                        now = datetime.now()
                        if (
                            self._last_429_time is None
                            or (now - self._last_429_time).total_seconds() > 600
                        ):
                            logger.warning("[视奸面板] 遥测请求频率超限 (429)")
                            self._last_429_time = now
                    else:
                        logger.debug(
                            "[视奸面板] 遥测事件发送失败: HTTP %s", response.status
                        )
            except asyncio.TimeoutError:
                logger.debug("[视奸面板] 遥测请求超时")
            except aiohttp.ClientError as exc:
                logger.debug("[视奸面板] 遥测网络请求异常: %s", exc)
            except Exception as exc:
                logger.debug("[视奸面板] 遥测发送未知异常: %s", exc)

        return False

    async def track_startup(self) -> bool:
        """上报启动事件与系统环境基础信息。"""
        return await self.track(
            "startup",
            {
                "os": platform.system(),
                "os_version": platform.release(),
                "python_version": platform.python_version(),
                "arch": platform.machine(),
                "astrbot_version": self._astrbot_version,
                "astrbot_version_source": self._astrbot_version_info.source,
                "astrbot_version_error": self._astrbot_version_info.error,
            },
            immediate=True,
        )

    async def track_shutdown(
        self,
        exit_code: int = 0,
        runtime_seconds: float = 0.0,
    ) -> bool:
        """上报退出事件。"""
        return await self.track(
            "shutdown",
            {
                "exit_code": exit_code,
                "runtime_seconds": max(0.0, runtime_seconds),
            },
            immediate=True,
            bypass_rate_limit=True,
        )

    async def track_heartbeat(self, uptime_seconds: float = 0.0) -> bool:
        """上报长稳运行心跳事件。"""
        return await self.track(
            "heartbeat",
            {
                "uptime_seconds": max(0.0, uptime_seconds),
            },
        )

    # 凭据类敏感键名集合
    _SENSITIVE_CREDENTIAL_KEYS = {
        "apikey",
        "refreshtoken",
        "accesstoken",
        "authtoken",
        "token",
        "secret",
        "password",
        "pwd",
        "cookie",
        "cookiestr",
        "appkey",
        "appsecret",
        "clientsecret",
        "authorization",
    }

    _CREDENTIAL_URL_KEY_PATTERN = (
        r"(?:token|key|secret|password|pwd|cookie|authorization|"
        r"api[-_]?key|refresh[-_]?token|access[-_]?token|auth[-_]?token|"
        r"app[-_]?key|app[-_]?secret|client[-_]?secret|cookie[-_]?str)"
    )

    @staticmethod
    def _normalize_credential_key(key: str) -> str:
        """规范化凭据键：转小写并去除特殊分隔符。"""
        return re.sub(r"[\s_\-]+", "", str(key).strip().lower())

    async def track_config(self, config: dict[str, Any]) -> bool:
        """上报脱敏后的配置快照。"""
        if not self._enabled:
            return False

        try:
            config_copy = copy.deepcopy(config)

            # 剔除可能包含用户隐私或认证凭据的键
            self._strip_sensitive_config_nodes(config_copy)
            self._sanitize_credentials(config_copy)

            return await self.track("config", config_copy, immediate=True)
        except Exception as exc:
            logger.debug("[视奸面板] 配置快照提取失败: %s", exc)
            return False

    def _strip_sensitive_config_nodes(self, node: Any) -> None:
        """递归删除配置中的隐私控制与敏感名单节点。"""
        if not isinstance(node, dict):
            return

        # 彻底移除黑名单与敏感配置项
        sensitive_keys = {
            "auth_token",
            "group_blacklist_sessions",
            "user_blacklist_senders",
            "info_blacklist_keywords",
            "info_blacklist_replacement",
            "device_whitelist_keywords",
            "device_blacklist_keywords",
        }
        for k in list(node.keys()):
            if k in sensitive_keys:
                del node[k]
            elif isinstance(node[k], (dict, list)):
                self._strip_sensitive_config_nodes(node[k])

    def _sanitize_credentials(self, node: Any) -> None:
        """递归对配置中残留的凭据进行安全替换。"""
        if isinstance(node, dict):
            for key in list(node.keys()):
                normalized = self._normalize_credential_key(key)
                if normalized in self._SENSITIVE_CREDENTIAL_KEYS:
                    node[key] = "***"
                elif isinstance(node[key], str):
                    if "=" in node[key] and ("?" in node[key] or "&" in node[key]):
                        node[key] = re.sub(
                            rf"(?i)([?&](?:{self._CREDENTIAL_URL_KEY_PATTERN})=)[^&\s\"']+",
                            r"\1***",
                            node[key],
                        )
                    else:
                        self._sanitize_credentials(node[key])
                else:
                    self._sanitize_credentials(node[key])
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                if isinstance(item, str) and (
                    "=" in item and ("?" in item or "&" in item)
                ):
                    node[idx] = re.sub(
                        rf"(?i)([?&](?:{self._CREDENTIAL_URL_KEY_PATTERN})=)[^&\s\"']+",
                        r"\1***",
                        item,
                    )
                else:
                    self._sanitize_credentials(item)

    async def track_feature(
        self, feature_name: str, extra: dict[str, Any] | None = None
    ) -> bool:
        """上报功能使用事件。"""
        data = extra.copy() if extra else {}
        data["feature"] = feature_name
        return await self.track("feature", data)

    async def track_error(
        self,
        exception: Exception,
        module: str | None = None,
    ) -> bool:
        """上报脱敏后的错误事件。"""
        module_name = module or "unknown"
        raw_message = str(exception)

        if self._should_skip_error_telemetry(exception, raw_message, module_name):
            return False

        sanitized_message = self._sanitize_message(raw_message)

        data = {
            "type": type(exception).__name__,
            "message": sanitized_message[:500],
            "module": module_name,
            "severity": "error",
        }

        stack = "".join(
            traceback.format_exception(
                type(exception),
                exception,
                exception.__traceback__,
            )
        )
        data["stack"] = self._sanitize_message(self._sanitize_stack(stack))[:4000]

        return await self.track("error", data)

    def _should_skip_error_telemetry(
        self,
        exception: Exception,
        raw_message: str,
        module: str | None = None,
    ) -> bool:
        """判断是否应跳过控制流或高频无价值错误。"""
        error_type = type(exception).__name__
        if error_type in {"CancelledError", "GeneratorExit"}:
            return True
        return False

    def _sanitize_stack(self, stack: str) -> str:
        """脱敏堆栈信息，剔除用户系统路径与私人用户名。"""
        stack = re.sub(r"[A-Za-z]:\\Users\\[^\\]+\\", r"<USER_HOME>\\", stack)
        stack = re.sub(r"/(?:home|Users|root)/[^/]+/", r"<USER_HOME>/", stack)
        stack = re.sub(r"/root/", r"<USER_HOME>/", stack)
        stack = re.sub(r".*astrbot_plugin_live_dashboard[/\\/]", r"<PLUGIN>/", stack)
        stack = re.sub(r".*site-packages[/\\/]", r"<SITE_PACKAGES>/", stack)
        return stack

    def _sanitize_message(self, message: str) -> str:
        """脱敏错误消息中的本地路径与 URL 凭据参数。"""
        message = re.sub(r"/(?:home|Users|root)/[^/\s]+/", r"<USER_HOME>/", message)
        message = re.sub(r"/root/", r"<USER_HOME>/", message)
        message = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+\\", r"<USER_HOME>\\", message)
        message = re.sub(
            rf"(?i)([?&](?:{self._CREDENTIAL_URL_KEY_PATTERN})=)[^&\s\"']+",
            r"\1***",
            message,
        )
        return message

    async def close(self) -> None:
        """幂等关闭遥测会话，完成未发送批次兜底并回收网络资源。"""
        if self._closed:
            return
        self._closed = True

        self._wake_event.set()
        if self._send_task and not self._send_task.done():
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass
            self._send_task = None

        try:
            await self.flush(bypass_rate_limit=True, _allow_after_close=True)
        except Exception as exc:
            logger.debug("[视奸面板] 关闭时兜底发送遥测失败（已忽略）: %s", exc)

        if self._session and not self._session.closed:
            try:
                await self._session.close()
            except Exception as exc:
                logger.debug("[视奸面板] 关闭遥测网络会话失败: %s", exc)
            finally:
                self._session = None
        logger.debug("[视奸面板] 遥测服务已安全关闭")


__all__ = ["TelemetryManager"]
