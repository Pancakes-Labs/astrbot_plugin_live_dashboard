"""AstrBot 插件入口文件。

维护约定：
- 本文件定义插件主类，供 AstrBot 扫描与加载。
- 业务细节仍下沉到 services / utils 层。
- 所有业务服务统一在 terminate 阶段释放。
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import astrbot.api.star as star
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Node, Nodes, Plain, Reply
from astrbot.api.provider import ProviderRequest

from .services.dashboard_service import DashboardService
from .services.friend_service import FriendService
from .services.health_service import HealthService
from .services.system_status_service import SystemStatusService
from .services.telemetry_service import TelemetryManager
from .services.telemetry_utils import track_feature_safely
from .services.timeline_service import TimelineService
from .utils.banner import print_banner
from .utils.config_parser import get_bool_value, get_text_value, parse_list_config
from .utils.version import get_plugin_version

# 好友面板子命令关键词（第二段参数）。
_FRIEND_SUBCOMMANDS = {
    "时间线": "timeline",
    "timeline": "timeline",
    "健康": "health",
    "health": "health",
    "健康数据": "health",
    "配置": "config",
    "config": "config",
}

# 长文合并转发阈值（字符数）。
_FORWARD_CHAR_THRESHOLD = 512


def _split_message_blocks(message: str) -> list[str]:
    """把渲染文本按空行分段，用于构建转发节点。"""
    blocks = [block.strip() for block in message.split("\n\n") if block.strip()]
    return blocks if blocks else [message.strip()]


def _parse_date_arg(raw: str | None) -> str | None:
    """解析命令参数中的日期（YYYY-MM-DD）。

    不支持/非法时返回 None，由服务层兜底为今天。
    """
    if not raw:
        return None
    value = raw.strip()
    if not value:
        return None
    # 仅接受完整的日期格式，其余交给服务层做格式校验提示。
    return value


def _parse_friend_args(raw: str | None) -> tuple[str | None, str | None, str | None]:
    """解析好友子命令参数。

    支持格式：
    - None / ""                → 列出面板
    - "小明"                    → 状态
    - "小明 时间线 [日期]"        → 时间线
    - "小明 健康 [日期]"         → 健康数据
    - "小明 配置"                → 站点配置

    Returns:
        (面板名或 None, 子命令或 None, 日期或 None)。
    """
    if not raw:
        return None, None, None
    tokens = [token for token in re.split(r"\s+", raw.strip()) if token]
    if not tokens:
        return None, None, None

    panel_name = tokens[0]
    subcommand: str | None = None
    date_arg: str | None = None

    if len(tokens) >= 2:
        normalized = _FRIEND_SUBCOMMANDS.get(tokens[1].lower(), None)
        if normalized:
            subcommand = normalized
            if len(tokens) >= 3:
                date_arg = tokens[2]
        # 第二个 token 不是子命令关键词时，视为纯状态查询（忽略多余文本）。

    return panel_name, subcommand, date_arg


class LiveDashboardPlugin(star.Star):
    """Live Dashboard 插件主类（扫描入口 + 命令入口）。

    合并转发组件（Nodes）目前仅 OneBot v11（aiocqhttp）平台可靠支持，
    此处把判断收敛为框架枚举单点，避免在代码中散落平台名字符串。
    """

    # 支持合并转发（Nodes）的平台：交给框架枚举语义表达。
    _FORWARD_CAPABLE_PLATFORM = filter.PlatformAdapterType.AIOCQHTTP.value

    def __init__(self, context: star.Context, config: dict[str, Any] | None = None):
        # 初始化 Star 基类。
        super().__init__(context)

        # 插件配置（由 AstrBot 注入）。
        self.config = config or {}
        self._start_time: float = time.monotonic()
        self._telemetry_tasks: set[asyncio.Task[None]] = set()
        self._heartbeat_task: asyncio.Task[None] | None = None

        # 启动横幅：打印 Pancakes-Labs ASCII art 横幅（bold_cyan 配色）。
        print_banner()

        # 业务服务：各自负责对应 API 的请求与渲染。
        self.dashboard_service = DashboardService(self.config)
        self.timeline_service = TimelineService(self.config)
        self.health_service = HealthService(self.config)
        self.friend_service = FriendService(self.config)
        self.system_status_service = SystemStatusService(self.config)

        # 初始化遥测管理器并注入各业务服务
        self.telemetry = TelemetryManager(
            config=self.config,
            plugin_version=get_plugin_version(),
        )
        for service in (
            self.dashboard_service,
            self.timeline_service,
            self.health_service,
            self.friend_service,
            self.system_status_service,
        ):
            if hasattr(service, "set_telemetry"):
                service.set_telemetry(self.telemetry)

        # 启动后台遥测任务（启动事件、配置快照与心跳循环）
        self._start_telemetry_tasks()

        logger.info(
            "[视奸面板] 插件初始化完成，服务地址=%s",
            get_text_value(self.config, "base_url", "") or "<未配置>",
        )

    def _start_telemetry_tasks(self) -> None:
        """启动阶段上报启动与配置遥测事件，并初始化心跳循环。"""
        if not self.telemetry or not self.telemetry.enabled:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        startup_task = loop.create_task(self.telemetry.track_startup())
        config_task = loop.create_task(self.telemetry.track_config(dict(self.config)))
        self._telemetry_tasks.add(startup_task)
        self._telemetry_tasks.add(config_task)
        startup_task.add_done_callback(self._telemetry_tasks.discard)
        config_task.add_done_callback(self._telemetry_tasks.discard)

        self._heartbeat_task = loop.create_task(self._heartbeat_loop())
        logger.debug("[视奸面板] 已启动遥测心跳任务 (间隔: 12小时)")

    async def _heartbeat_loop(self) -> None:
        """遥测心跳定时上报循环。"""
        heartbeat_interval = 43200  # 12 小时
        try:
            while self.telemetry and self.telemetry.enabled:
                await asyncio.sleep(heartbeat_interval)
                uptime = time.monotonic() - self._start_time
                await self.telemetry.track_heartbeat(uptime_seconds=uptime)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.debug("[视奸面板] 遥测心跳异常: %s", exc)

    async def _cleanup_telemetry_tasks(self) -> None:
        """清理并等待所有未完成的遥测任务。"""
        if not self._telemetry_tasks:
            return
        pending_tasks = list(self._telemetry_tasks)
        for task in pending_tasks:
            if not task.done():
                task.cancel()
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)
        self._telemetry_tasks.clear()

    def _get_query_denied_text(self, event: AstrMessageEvent) -> str | None:
        """统一处理黑名单拦截，命中时返回拒绝文案。"""
        sender_id = str(event.get_sender_id() or "").strip()
        session_id = str(getattr(event.message_obj, "session_id", "") or "").strip()

        # 群/用户黑名单都来自配置文本，先统一解析成列表。
        group_blacklist = parse_list_config(
            get_text_value(self.config, "group_blacklist_sessions", "")
        )
        user_blacklist = parse_list_config(
            get_text_value(self.config, "user_blacklist_senders", "")
        )

        # 兼容两种群黑名单写法：完整 session_id 或仅群号（后缀匹配）。
        is_group_blocked = bool(session_id) and any(
            blocked == session_id or session_id.endswith(f":{blocked}")
            for blocked in group_blacklist
        )
        if is_group_blocked:
            logger.info("[视奸面板] 群组黑名单命中，拒绝查询：会话=%s", session_id)
            return "该群组已禁用状态查询喵。"

        is_user_blocked = bool(sender_id) and any(
            blocked == sender_id for blocked in user_blacklist
        )
        if is_user_blocked:
            logger.info("[视奸面板] 用户黑名单命中，拒绝查询：发送者ID：%s", sender_id)
            return "你已被禁止使用该查询喵。"

        return None

    def _is_known_error(self, message: str) -> bool:
        """识别服务层返回的可读错误前缀，避免把失败包装成成功。"""
        known_error_prefixes = (
            "未配置 Live Dashboard 地址",
            "日期格式不正确：",
            "请求超时：",
            "鉴权失败：",
            "请求失败：",
            "网络错误：",
            "响应异常：",
            "发生未预期错误：",
        )
        return message.startswith(known_error_prefixes)

    def _build_forward_nodes(self, event: AstrMessageEvent, message: str) -> Nodes:
        """把文本按空行分段构建为合并转发节点（首节点携带回复引用）。

        合并转发仅对支持该组件的平台启用，判断交给框架的枚举语义，插件不硬编码平台名字符串。
        """
        blocks = _split_message_blocks(message)
        node_name = "Live Dashboard"
        node_uin = event.get_self_id() or "0"

        first_block = blocks[0] if blocks else message
        forward_nodes: list[Node] = [
            Node(
                uin=node_uin,
                name=node_name,
                content=[
                    Reply(id=event.message_obj.message_id),
                    Plain(text=first_block),
                ],
            )
        ]

        for block in blocks[1:]:
            forward_nodes.append(
                Node(
                    uin=node_uin,
                    name=node_name,
                    content=[Plain(text=block)],
                )
            )

        return Nodes(nodes=forward_nodes)

    async def _query_dashboard_message(self) -> tuple[str, int]:
        """复用核心查询逻辑，返回渲染文本与展示设备数量。"""
        return await self.dashboard_service.query_and_render()

    def _build_response_components(
        self, event: AstrMessageEvent, message: str
    ) -> list[Plain | Nodes]:
        """构建回复组件：支持合并转发时返回转发节点，否则降级为纯文本。

        判断逻辑：
        - 仅 aiocqhttp 平台且文本超过阈值时使用合并转发（Nodes）；
        - 其他平台（或文本较短）一律降级为 Plain 纯文本发送，
          保证所有平台都能收到完整内容。
        """
        if (
            event.get_platform_name() == self._FORWARD_CAPABLE_PLATFORM
            and len(message) > _FORWARD_CHAR_THRESHOLD
        ):
            return [self._build_forward_nodes(event, message)]

        # 降级路径：非 aiocqhttp 平台或文本未超阈值 → 纯文本。
        return [Plain(text=message)]

    # ── LLM 工具提示注入 ──────────────────────────────────────────────

    @filter.on_llm_request()
    async def inject_live_dashboard_tool_prompt(
        self, event: AstrMessageEvent, req: ProviderRequest
    ):
        """在 LLM 请求前注入工具使用提示，提升自动调用命中率。"""
        # 该段会直接拼接到 system_prompt，作为工具调用策略提示。
        instruction = (
            "\n\n[Live Dashboard (视奸面板) 工具使用规范]\n"
            "- 工具 query_live_dashboard_status：获取用户的实时设备状态（无需参数）。"
            "当用户询问“来视奸我/我现在在干嘛/帮我视奸一下他在干什么/设备在线情况/状态面板/最近在用什么应用”时优先调用。\n"
            "- 工具 query_live_dashboard_timeline：查询指定日期的应用使用时间线（参数 date 可选，YYYY-MM-DD，缺省今天）。\n"
            "- 工具 query_live_dashboard_health：查询指定日期的健康数据（参数 date 可选，YYYY-MM-DD，缺省今天）。\n"
            "- 工具 query_friend_dashboard_status：查询指定好友面板的实时状态（参数 name 必填，可填面板名称或 id）。\n"
            "- 若返回的是权限或配置错误提示，请向用户明确说明原因并给出简短建议，不要编造实时数据。\n"
            "- 获得工具结果后，请按你的人设组织回复。\n"
        )
        req.system_prompt = (req.system_prompt or "") + instruction

    # ── LLM 工具：实时状态 ────────────────────────────────────────────

    @filter.llm_tool(name="query_live_dashboard_status")
    async def query_live_dashboard_status_tool(self, event: AstrMessageEvent) -> str:
        """查询 Live Dashboard 实时设备状态，供 LLM 在对话中自动调用。

        Args:
            event(object): AstrBot 消息事件上下文（由框架注入）。
        """
        user_id = str(event.get_sender_id() or "").strip()
        bot_id = str(event.get_self_id() or "").strip()
        session_id = str(getattr(event.message_obj, "session_id", "") or "").strip()
        logger.info(
            "[视奸面板] LLM 工具触发状态查询，机器人ID：%s, 用户ID：%s, 会话：%s",
            bot_id or "未知",
            user_id or "未知",
            session_id or "未知",
        )

        denied_text = self._get_query_denied_text(event)
        if denied_text:
            await track_feature_safely(
                self.telemetry,
                "llm_tool_status",
                {"success": False, "blocked": True},
            )
            return denied_text

        message, render_device_count = await self._query_dashboard_message()
        is_error = self._is_known_error(message)

        await track_feature_safely(
            self.telemetry,
            "llm_tool_status",
            {"success": not is_error, "blocked": False},
        )

        if is_error:
            return f"实时状态查询失败：{message}"

        return (
            f"实时状态查询成功，当前展示设备数：{render_device_count}。\n"
            "以下为状态面板原始文本：\n"
            f"{message}"
        )

    # ── LLM 工具：时间线 ──────────────────────────────────────────────

    @filter.llm_tool(name="query_live_dashboard_timeline")
    async def query_live_dashboard_timeline_tool(
        self, event: AstrMessageEvent, date: str | None = None
    ) -> str:
        """查询指定日期的应用使用时间线，供 LLM 在对话中自动调用。

        Args:
            event(object): AstrBot 消息事件上下文（由框架注入）。
            date(string): 可选，YYYY-MM-DD；缺省为今天。
        """
        user_id = str(event.get_sender_id() or "").strip()
        session_id = str(getattr(event.message_obj, "session_id", "") or "").strip()
        logger.info(
            "[视奸面板] LLM 工具触发时间线查询，用户ID：%s, 会话：%s, 日期：%s",
            user_id or "未知",
            session_id or "未知",
            date or "今天",
        )
        if not get_bool_value(self.config, "enable_timeline_command", True):
            return "时间线查询已禁用喵。"

        denied_text = self._get_query_denied_text(event)
        if denied_text:
            await track_feature_safely(
                self.telemetry,
                "llm_tool_timeline",
                {"success": False, "blocked": True},
            )
            return denied_text

        message, _ = await self.timeline_service.query_and_render(
            date=_parse_date_arg(date)
        )
        is_error = self._is_known_error(message)

        await track_feature_safely(
            self.telemetry,
            "llm_tool_timeline",
            {"success": not is_error, "blocked": False},
        )

        if is_error:
            return f"时间线查询失败：{message}"
        return f"时间线查询成功，以下为 {date or '今天'} 的时间线原始文本：\n{message}"

    # ── LLM 工具：健康数据 ────────────────────────────────────────────

    @filter.llm_tool(name="query_live_dashboard_health")
    async def query_live_dashboard_health_tool(
        self, event: AstrMessageEvent, date: str | None = None
    ) -> str:
        """查询指定日期的健康数据，供 LLM 在对话中自动调用。

        Args:
            event(object): AstrBot 消息事件上下文（由框架注入）。
            date(string): 可选，YYYY-MM-DD；缺省为今天。
        """
        user_id = str(event.get_sender_id() or "").strip()
        session_id = str(getattr(event.message_obj, "session_id", "") or "").strip()
        logger.info(
            "[视奸面板] LLM 工具触发健康数据查询，用户ID：%s, 会话：%s, 日期：%s",
            user_id or "未知",
            session_id or "未知",
            date or "今天",
        )
        if not get_bool_value(self.config, "enable_health_command", True):
            return "健康数据查询已禁用喵。"

        denied_text = self._get_query_denied_text(event)
        if denied_text:
            await track_feature_safely(
                self.telemetry,
                "llm_tool_health",
                {"success": False, "blocked": True},
            )
            return denied_text

        message = await self.health_service.query_and_render(date=_parse_date_arg(date))
        is_error = self._is_known_error(message)

        await track_feature_safely(
            self.telemetry,
            "llm_tool_health",
            {"success": not is_error, "blocked": False},
        )

        if is_error:
            return f"健康数据查询失败：{message}"
        return (
            f"健康数据查询成功，以下为 {date or '今天'} 的健康数据原始文本：\n{message}"
        )

    # ── LLM 工具：好友面板 ────────────────────────────────────────────

    @filter.llm_tool(name="query_friend_dashboard_status")
    async def query_friend_dashboard_status_tool(
        self, event: AstrMessageEvent, name: str = ""
    ) -> str:
        """查询指定好友面板的实时状态，供 LLM 在对话中自动调用。

        Args:
            event(object): AstrBot 消息事件上下文（由框架注入）。
            name(string): 好友面板名称或 id（必填）。
        """
        user_id = str(event.get_sender_id() or "").strip()
        session_id = str(getattr(event.message_obj, "session_id", "") or "").strip()
        logger.info(
            "[视奸面板] LLM 工具触发好友面板查询，用户ID：%s, 会话：%s, 面板：%s",
            user_id or "未知",
            session_id or "未知",
            name or "（全部）",
        )
        if not get_bool_value(self.config, "enable_friend_command", True):
            return "好友面板查询已禁用喵。"

        denied_text = self._get_query_denied_text(event)
        if denied_text:
            await track_feature_safely(
                self.telemetry,
                "llm_tool_friend",
                {"success": False, "blocked": True},
            )
            return denied_text

        if not name or not name.strip():
            dashboards, error = await self.friend_service.list_friends()
            await track_feature_safely(
                self.telemetry,
                "llm_tool_friend",
                {"success": not bool(error), "list_mode": True, "blocked": False},
            )
            if error:
                return f"好友面板列表查询失败：{error}"
            if not dashboards:
                return "当前未配置任何好友面板喵。"
            names = "、".join(str(d.get("name", "?")) for d in dashboards)
            return f"当前已配置的好友面板：{names}"

        message, ok = await self.friend_service.query_friend_status(name)
        await track_feature_safely(
            self.telemetry,
            "llm_tool_friend",
            {"success": ok, "list_mode": False, "blocked": False},
        )
        if not ok:
            return f"好友面板查询失败：{message}"
        return f"好友面板查询成功：\n{message}"

    # ── 命令：实时状态 ────────────────────────────────────────────────

    @filter.command("视奸", alias={"livedashboard", "ldb", "设备状态", "状态面板"})
    async def query_live_dashboard(self, event: AstrMessageEvent):
        """状态查询命令处理器。"""
        sender_id = str(event.get_sender_id() or "").strip()
        session_id = str(getattr(event.message_obj, "session_id", "") or "").strip()

        logger.info(
            "[视奸面板] 收到状态查询指令，发送者：%s, 会话：%s",
            sender_id or "未知",
            session_id or "未知",
        )

        denied_text = self._get_query_denied_text(event)
        if denied_text:
            await track_feature_safely(
                self.telemetry,
                "command_status",
                {"success": False, "blocked": True},
            )
            yield event.chain_result(
                [
                    Reply(id=event.message_obj.message_id),
                    Plain(text=denied_text),
                ]
            )
            return

        message, render_device_count = await self._query_dashboard_message()
        is_error = self._is_known_error(message)

        # 仅在支持合并转发的平台且设备较多时启用合并转发，减少刷屏。
        use_forward_mode = (
            render_device_count >= 2
            and event.get_platform_name() == self._FORWARD_CAPABLE_PLATFORM
        )

        await track_feature_safely(
            self.telemetry,
            "command_status",
            {
                "success": not is_error,
                "forward_mode": use_forward_mode,
                "blocked": False,
            },
        )

        # 设备较少：直接引用 + 全量文本。
        if not use_forward_mode:
            yield event.chain_result(
                [Reply(id=event.message_obj.message_id), Plain(text=message)]
            )
            return

        # 设备较多：仅发送一条合并转发；在首节点里包含引用消息，避免额外刷屏。
        yield event.chain_result([self._build_forward_nodes(event, message)])

    # ── 命令：服务状态 ────────────────────────────────────────────────

    @filter.command("视奸服务状态")
    async def query_system_status(self, event: AstrMessageEvent):
        """服务状态查询命令：检查 Live Dashboard 连通性、运行时长与时间。"""
        if not get_bool_value(self.config, "enable_system_status_command", True):
            yield event.chain_result([Plain(text="服务状态查询已禁用喵。")])
            return

        denied_text = self._get_query_denied_text(event)
        if denied_text:
            await track_feature_safely(
                self.telemetry,
                "command_system_status",
                {"success": False, "blocked": True},
            )
            yield event.chain_result([Plain(text=denied_text)])
            return

        logger.info(
            "[视奸面板] 收到服务状态查询指令，会话：%s",
            str(getattr(event.message_obj, "session_id", "") or ""),
        )
        message = await self.system_status_service.query_and_render()
        is_error = self._is_known_error(message)

        await track_feature_safely(
            self.telemetry,
            "command_system_status",
            {"success": not is_error, "blocked": False},
        )
        yield event.chain_result([Plain(text=message)])

    # ── 命令：时间线 ──────────────────────────────────────────────────

    @filter.command("视奸时间线", alias={"视奸历史"})
    async def query_timeline(self, event: AstrMessageEvent, date: str | None = None):
        """时间线查询命令处理器：查询指定日期（缺省今天）每个应用的使用时长。"""
        if not get_bool_value(self.config, "enable_timeline_command", True):
            yield event.chain_result([Plain(text="时间线查询已禁用喵。")])
            return

        denied_text = self._get_query_denied_text(event)
        if denied_text:
            await track_feature_safely(
                self.telemetry,
                "command_timeline",
                {"success": False, "blocked": True},
            )
            yield event.chain_result([Plain(text=denied_text)])
            return

        target_date = _parse_date_arg(date)
        logger.info(
            "[视奸面板] 收到时间线查询指令，日期：%s，会话：%s",
            target_date or "今天",
            str(getattr(event.message_obj, "session_id", "") or ""),
        )

        message, segment_count = await self.timeline_service.query_and_render(
            date=target_date
        )
        is_error = self._is_known_error(message)

        await track_feature_safely(
            self.telemetry,
            "command_timeline",
            {"success": not is_error, "blocked": False},
        )
        yield event.chain_result(self._build_response_components(event, message))

    # ── 命令：健康数据 ────────────────────────────────────────────────

    @filter.command("视奸健康", alias={"健康数据"})
    async def query_health(self, event: AstrMessageEvent, date: str | None = None):
        """健康数据查询命令处理器：查询指定日期（缺省今天）的心率/步数/睡眠等。"""
        if not get_bool_value(self.config, "enable_health_command", True):
            yield event.chain_result([Plain(text="健康数据查询已禁用喵。")])
            return

        denied_text = self._get_query_denied_text(event)
        if denied_text:
            await track_feature_safely(
                self.telemetry,
                "command_health",
                {"success": False, "blocked": True},
            )
            yield event.chain_result([Plain(text=denied_text)])
            return

        target_date = _parse_date_arg(date)
        logger.info(
            "[视奸面板] 收到健康数据查询指令，日期：%s，会话：%s",
            target_date or "今天",
            str(getattr(event.message_obj, "session_id", "") or ""),
        )

        message = await self.health_service.query_and_render(date=target_date)
        is_error = self._is_known_error(message)

        await track_feature_safely(
            self.telemetry,
            "command_health",
            {"success": not is_error, "blocked": False},
        )
        yield event.chain_result(self._build_response_components(event, message))

    # ── 命令：好友面板（含子命令） ────────────────────────────────────

    @filter.command("视奸好友", alias={"好友面板"})
    async def query_friend(self, event: AstrMessageEvent, name: str | None = None):
        """好友面板查询命令处理器。

        支持子命令：
        - 无参数：列出所有面板
        - <名称>：查询实时状态
        - <名称> 时间线 [日期]：查询时间线
        - <名称> 健康 [日期]：查询健康数据
        - <名称> 配置：查询站点配置
        """
        if not get_bool_value(self.config, "enable_friend_command", True):
            yield event.chain_result([Plain(text="好友面板查询已禁用喵。")])
            return

        denied_text = self._get_query_denied_text(event)
        if denied_text:
            await track_feature_safely(
                self.telemetry,
                "command_friend",
                {"success": False, "blocked": True},
            )
            yield event.chain_result([Plain(text=denied_text)])
            return

        panel_name, subcommand, date_arg = _parse_friend_args(name)
        logger.info(
            "[视奸面板] 收到好友面板查询指令，面板：%s，子命令：%s，日期：%s，会话：%s",
            panel_name or "（全部）",
            subcommand or "状态",
            date_arg or "-",
            str(getattr(event.message_obj, "session_id", "") or ""),
        )

        # 未指定面板名：列出所有可用面板。
        if not panel_name:
            dashboards, error = await self.friend_service.list_friends()
            await track_feature_safely(
                self.telemetry,
                "command_friend",
                {"subcommand": "list", "success": not bool(error), "blocked": False},
            )
            if error:
                yield event.chain_result([Plain(text=error)])
                return
            if not dashboards:
                yield event.chain_result([Plain(text="当前未配置任何好友面板喵。")])
                return
            names = "、".join(str(d.get("name", "?")) for d in dashboards)
            yield event.chain_result(
                [
                    Plain(
                        text=(
                            "👥 当前已配置的好友面板：\n"
                            f"{names}\n\n"
                            "使用「好友 <名称>」查看实时状态，"
                            "「好友 <名称> 时间线/健康/配置」查看对应数据喵。"
                        )
                    )
                ]
            )
            return

        # 按子命令分发。
        if subcommand == "timeline":
            message, ok = await self.friend_service.query_friend_timeline(
                panel_name, date=_parse_date_arg(date_arg)
            )
            await track_feature_safely(
                self.telemetry,
                "command_friend",
                {"subcommand": "timeline", "success": ok, "blocked": False},
            )
            if not ok:
                yield event.chain_result([Plain(text=message)])
                return
            yield event.chain_result(self._build_response_components(event, message))
            return

        if subcommand == "health":
            message, ok = await self.friend_service.query_friend_health(
                panel_name, date=_parse_date_arg(date_arg)
            )
            await track_feature_safely(
                self.telemetry,
                "command_friend",
                {"subcommand": "health", "success": ok, "blocked": False},
            )
            if not ok:
                yield event.chain_result([Plain(text=message)])
                return
            yield event.chain_result(self._build_response_components(event, message))
            return

        if subcommand == "config":
            message, ok = await self.friend_service.query_friend_config(panel_name)
            await track_feature_safely(
                self.telemetry,
                "command_friend",
                {"subcommand": "config", "success": ok, "blocked": False},
            )
            result_text = message if ok else f"查询失败：{message}"
            yield event.chain_result([Plain(text=result_text)])
            return

        # 默认：实时状态。
        message, ok = await self.friend_service.query_friend_status(panel_name)
        await track_feature_safely(
            self.telemetry,
            "command_friend",
            {"subcommand": "status", "success": ok, "blocked": False},
        )
        result_text = message if ok else f"查询失败：{message}"
        yield event.chain_result([Plain(text=result_text)])

    async def terminate(self):
        """插件停用/卸载时的资源释放入口。"""
        logger.info("[视奸面板] 正在停止视奸面板插件...")

        # 1. 停止心跳任务与上报退出事件（单独 try 包裹，避免阻塞资源清理）
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        if hasattr(self, "telemetry") and self.telemetry and self.telemetry.enabled:
            try:
                runtime_seconds = time.monotonic() - getattr(
                    self, "_start_time", time.monotonic()
                )
                await self.telemetry.track_shutdown(
                    exit_code=0,
                    runtime_seconds=max(0.0, runtime_seconds),
                )
            except Exception as exc:
                logger.debug("[视奸面板] 退出事件上报失败（已忽略）: %s", exc)

        # 2. 清理未完成的后台遥测任务
        try:
            await self._cleanup_telemetry_tasks()
        except Exception as exc:
            logger.debug("[视奸面板] 清理遥测任务失败（已忽略）: %s", exc)

        # 3. 业务服务资源释放
        failures: list[str] = []
        services = (
            self.dashboard_service,
            self.timeline_service,
            self.health_service,
            self.friend_service,
            self.system_status_service,
        )
        for service in services:
            try:
                await service.close()
            except Exception as exc:  # noqa: BLE001
                logger.exception("[视奸面板] 资源清理阶段出现异常：%s", exc)
                failures.append(type(service).__name__)
        if failures:
            logger.warning("[视奸面板] 部分服务释放失败：%s", ", ".join(failures))

        # 4. 关闭底层遥测网络会话
        if hasattr(self, "telemetry") and self.telemetry:
            try:
                await self.telemetry.close()
            except Exception as exc:
                logger.debug("[视奸面板] 遥测网络会话关闭失败（已忽略）: %s", exc)

        logger.info("[视奸面板] 视奸面板插件已停止")


__all__ = ["LiveDashboardPlugin"]
