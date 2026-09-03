"""实时状态消息渲染层。

职责：
- 消费上游 /api/current 的权威字段（status_text / display_title / extra），
  产出可直接发送的文本。
- 状态文案以服务端 status_text 为准；display_title 已由服务端按隐私分级净化，
  仅做占位值归一与长度保护，不再本地复刻任何应用名→文案逻辑。
- 读侧 NSFW 兜底：对服务端可能残留的敏感标题在执行隐私打码后再补一道过滤。
"""

from __future__ import annotations

from typing import Any

# 日志对象：用于记录渲染链路的调试信息（主要使用 DEBUG）。
from astrbot.api import logger

# 配置读取工具：统一处理类型转换和默认值。
from ..utils.config_parser import (
    get_bool_value,
    get_int_value,
    get_text_value,
    parse_list_config,
)
from ..utils.nsfw_filter import is_nsfw
from ..utils.text_utils import NSFW_MASK_TEXT, clean_text, mask_sensitive_text
from ..utils.time_formatter import format_relative_time, format_time_text

# 服务端上常见的占位标题（与上游回写行为对齐，非本地复刻映射）。
_DISPLAY_TITLE_PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "unknown",
        "android",
        "windows",
        "macos",
        "linux",
        "null",
        "none",
    }
)

# 常见消息平台（作为 app_id 上交时属于占位，不展示成应用名）。
_PLATFORM_APP_NAME_VALUES = frozenset(
    {"android", "windows", "macos", "linux", "ios", "iphone", "ipad"}
)

# display_title 超长时截断，避免单行刷屏。
_MAX_TITLE_LENGTH = 120


def _is_online(device_item: dict[str, Any]) -> bool:
    """判断设备是否在线。

    兼容上游返回的数值（1/0）与通用布尔形态。
    """
    value = device_item.get("is_online", 0)

    # 布尔值直接返回。
    if isinstance(value, bool):
        return value
    # 数值按 1 表示在线。
    if isinstance(value, int):
        return value == 1
    # 字符串做兼容解析。
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true"}

    # 其他未知类型默认按离线处理（保守策略）。
    return False


def _friendly_app_name(app_name: str) -> str:
    """应用名展示值：空值 / 平台占位统一为「未识别应用」。"""
    name = app_name.strip()
    if not name or name.lower() in _PLATFORM_APP_NAME_VALUES:
        return "未识别应用"
    return name


def _normalize_display_title(display_title: str) -> str:
    """轻量归一 display_title：去占位值并截断超长标题。"""
    title = display_title.strip()
    if not title:
        return ""
    if title.lower() in _DISPLAY_TITLE_PLACEHOLDER_VALUES:
        return ""
    if len(title) > _MAX_TITLE_LENGTH:
        title = title[: _MAX_TITLE_LENGTH - 1].rstrip() + "…"
    return title


def _format_battery(extra_data: dict[str, Any]) -> str:
    """格式化电量文本。"""
    battery_percent = extra_data.get("battery_percent")
    battery_charging = extra_data.get("battery_charging")

    if not isinstance(battery_percent, (int, float)):
        return "未知"

    percent_text = f"{round(float(battery_percent))}%"
    if isinstance(battery_charging, bool):
        return f"{percent_text} {'⚡充电中' if battery_charging else '未充电'}"
    return percent_text


def _format_music(extra_data: dict[str, Any]) -> str:
    """格式化音乐信息文本（来自服务端 extra.music）。"""
    music_data = extra_data.get("music")
    if not isinstance(music_data, dict):
        return "暂无播放"

    title_text = clean_text(music_data.get("title"))
    artist_text = clean_text(music_data.get("artist"))
    app_text = clean_text(music_data.get("app"))

    if not any((title_text, artist_text, app_text)):
        return "暂无播放"

    if title_text and artist_text:
        core_text = f"{artist_text} - {title_text}"
    else:
        core_text = title_text or artist_text

    if app_text:
        return f"{core_text} ({app_text})" if core_text else app_text
    return core_text or "暂无播放"


def _format_server_time(server_time: Any) -> str:
    """格式化服务端时间字段。"""
    if isinstance(server_time, str) and server_time.strip():
        return format_time_text(server_time)
    return ""


def select_devices_for_render(
    payload_data: dict[str, Any], config: dict[str, Any]
) -> tuple[list[dict[str, Any]], int, int]:
    """按配置筛选并排序设备，返回 (展示列表, 在线数, 总数)。

    - 总数 / 在线数基于筛选后的设备集合计算，与展示设备数区分。
    - 白名单 / 黑名单仅匹配 device_name，黑名单优先级更高。
    """
    all_devices_raw = payload_data.get("devices", [])
    all_devices = (
        [item for item in all_devices_raw if isinstance(item, dict)]
        if isinstance(all_devices_raw, list)
        else []
    )

    whitelist_keywords = parse_list_config(
        get_text_value(config, "device_whitelist_keywords", ""), to_lower=True
    )
    blacklist_keywords = parse_list_config(
        get_text_value(config, "device_blacklist_keywords", ""), to_lower=True
    )

    counted = all_devices
    if whitelist_keywords:
        counted = [
            item
            for item in counted
            if any(
                k in clean_text(item.get("device_name")).lower()
                for k in whitelist_keywords
            )
        ]
    if blacklist_keywords:
        counted = [
            item
            for item in counted
            if not any(
                k in clean_text(item.get("device_name")).lower()
                for k in blacklist_keywords
            )
        ]

    total_count = len(counted)
    online_count = sum(1 for item in counted if _is_online(item))

    include_offline_devices = get_bool_value(config, "include_offline_devices", False)
    max_devices = get_int_value(config, "max_devices", 10, min_value=1, max_value=100)

    device_items = counted
    if not include_offline_devices:
        device_items = [item for item in device_items if _is_online(item)]

    # 在线优先，其次按设备名排序，保证输出顺序稳定。
    device_items.sort(
        key=lambda item: (
            0 if _is_online(item) else 1,
            clean_text(item.get("device_name")),
        )
    )

    return device_items[:max_devices], online_count, total_count


def render_dashboard_message_with_count(
    payload_data: dict[str, Any], config: dict[str, Any]
) -> tuple[str, int]:
    """渲染实时状态文本并返回展示设备数，避免调用方重复计算。"""
    device_items, online_count, total_count = select_devices_for_render(
        payload_data, config
    )

    # 读取所有显示开关（由 _conf_schema.json 定义）。
    show_platform = get_bool_value(config, "show_platform", True)
    show_app_name = get_bool_value(config, "show_app_name", True)
    show_display_title = get_bool_value(config, "show_display_title", True)
    show_battery = get_bool_value(config, "show_battery", True)
    show_music = get_bool_value(config, "show_music", True)
    show_last_seen = get_bool_value(config, "show_last_seen", True)
    show_viewer_count = get_bool_value(config, "show_viewer_count", False)
    show_server_time = get_bool_value(config, "show_server_time", False)
    show_recent_activities = get_bool_value(config, "show_recent_activities", False)
    recent_activities_max = get_int_value(
        config, "recent_activities_max", 5, min_value=1, max_value=20
    )
    info_blacklist_keywords = parse_list_config(
        get_text_value(config, "info_blacklist_keywords", ""), to_lower=True
    )
    info_blacklist_replacement = (
        get_text_value(
            config, "info_blacklist_replacement", "不想让你看到我在干什么喵~"
        )
        or "不想让你看到我在干什么喵~"
    )

    lines: list[str] = [
        "📊 Live Dashboard 状态面板",
        f"在线设备：{online_count}/{total_count}",
    ]

    logger.debug(
        "[视奸面板] 开始渲染消息，设备总数：%s, 在线数：%s, 展示数：%s",
        total_count,
        online_count,
        len(device_items),
    )

    # 可选展示访客数。
    if show_viewer_count:
        viewer_count = payload_data.get("viewer_count")
        if isinstance(viewer_count, int):
            lines.append(f"当前访客：{viewer_count}")

    # 可选展示服务端时间。
    if show_server_time:
        server_time_text = _format_server_time(payload_data.get("server_time"))
        if server_time_text:
            lines.append(f"服务端时间：{server_time_text}")

    if not device_items:
        lines.append("")
        lines.append("暂无符合条件的设备状态喵。")
        return "\n".join(lines), 0

    lines.append("")

    # 逐台设备渲染。
    for device_item in device_items:
        device_name = clean_text(device_item.get("device_name")) or "未知设备"
        platform_text = clean_text(device_item.get("platform")) or "unknown"
        status_online = _is_online(device_item)
        status_text = "在线" if status_online else "离线"

        app_name_raw = clean_text(device_item.get("app_name"))
        display_title_raw = clean_text(device_item.get("display_title"))
        extra_data = device_item.get("extra", {})
        if not isinstance(extra_data, dict):
            extra_data = {}

        # 设备首行：设备名 + 在线状态 + 平台（可选）。
        head_text = f"• {device_name} [{status_text}]"
        if show_platform:
            head_text += f" ({platform_text})"
        lines.append(head_text)

        # 主叙事句：优先服务端 status_text，缺失时兜底。
        if status_online:
            status_text_value = clean_text(device_item.get("status_text"))
            activity_text = status_text_value or "正在忙别的喵~"
        else:
            activity_text = "离线休息中喵~"

        activity_text = mask_sensitive_text(
            activity_text,
            info_blacklist_keywords,
            info_blacklist_replacement,
        )
        lines.append(f"  现在：{activity_text}")

        # 应用名（可选）：命中信息黑名单关键词时替换为统一文案。
        if show_app_name:
            app_name_text = _friendly_app_name(app_name_raw)
            app_name_text = mask_sensitive_text(
                app_name_text,
                info_blacklist_keywords,
                info_blacklist_replacement,
            )
            lines.append(f"  应用：{app_name_text}")

        # display_title（可选）：服务端已按隐私分级净化，仅做占位/长度归一。
        if show_display_title:
            normalized_title = _normalize_display_title(display_title_raw)
            # 与上游前端对齐的去重：
            # - display_title 包含正在播放的歌名（音乐行已展示）时不再重复展示；
            # - display_title 与应用名一字不差时视为零信息。
            music_raw = extra_data.get("music")
            music_title_text = (
                clean_text(music_raw.get("title"))
                if isinstance(music_raw, dict)
                else ""
            )
            title_is_redundant = (
                bool(music_title_text)
                and music_title_text.lower() in normalized_title.lower()
            ) or (
                bool(app_name_raw) and normalized_title.lower() == app_name_raw.lower()
            )
            if not normalized_title or title_is_redundant:
                lines.append("  标题：（无可展示标题）")
            else:
                # 读侧 NSFW 兜底：命中黑名单则整体打码。
                if is_nsfw(app_name_raw, normalized_title):
                    lines.append(f"  标题：{NSFW_MASK_TEXT}")
                else:
                    masked = mask_sensitive_text(
                        normalized_title,
                        info_blacklist_keywords,
                        info_blacklist_replacement,
                    )
                    lines.append(f"  标题：{masked or '（无可展示标题）'}")

        # 电量（可选）：仅在线设备展示。离线时 extra 是最后上报的残留值，
        # 展示易误导（与上游仅在线设备展示电量的行为对齐）。
        if show_battery and status_online:
            lines.append(f"  🔋 电量：{_format_battery(extra_data)}")

        # 音乐（可选）：同上，仅在线设备展示。
        if show_music and status_online:
            lines.append(f"  🎵 音乐：{_format_music(extra_data)}")

        # 最后上报时间（可选）。
        if show_last_seen:
            last_seen = device_item.get("last_seen_at")
            if isinstance(last_seen, str) and last_seen.strip():
                lines.append(f"  🕒 上报：{format_time_text(last_seen)}")
            else:
                lines.append("  🕒 上报：暂无上报")

        # 每台设备之间留一个空行。
        lines.append("")

    # 可选：展示最近活动（recent_activities 由上游按 started_at 倒序返回）。
    if show_recent_activities:
        recent_raw = payload_data.get("recent_activities", [])
        recent_items = (
            [r for r in recent_raw if isinstance(r, dict)]
            if isinstance(recent_raw, list)
            else []
        )
        if recent_items:
            # 设备列表尾部已留有尾随空行，仅当上一行非空时才补空行（修复多余换行）。
            if lines and lines[-1].strip():
                lines.append("")

            # 方案A：设备信息上浮。单设备时上浮到区块标题；多设备时按设备分组，
            # 仅在设备切换处重新标注设备名，避免每行重复超长设备字符串。
            recent_slice = recent_items[:recent_activities_max]
            device_names: list[str] = []
            for _activity in recent_slice:
                _device = clean_text(_activity.get("device_name"))
                if _device and _device not in device_names:
                    device_names.append(_device)
            single_device = len(device_names) == 1

            if single_device:
                lines.append(f"最近活动（{device_names[0]}）：")
            else:
                lines.append("最近活动：")

            current_device: str | None = None
            for index, activity in enumerate(recent_slice):
                activity_app_raw = clean_text(activity.get("app_name"))
                activity_app = _friendly_app_name(activity_app_raw)
                activity_status = clean_text(activity.get("status_text"))
                activity_title = _normalize_display_title(
                    clean_text(activity.get("display_title"))
                )
                activity_device = clean_text(activity.get("device_name"))
                activity_time_raw = activity.get("started_at")
                activity_time = (
                    format_relative_time(activity_time_raw)
                    if isinstance(activity_time_raw, str) and activity_time_raw.strip()
                    else ""
                )
                main_text = activity_status or activity_app or "未知活动"
                main_text = mask_sensitive_text(
                    main_text,
                    info_blacklist_keywords,
                    info_blacklist_replacement,
                )
                # 与设备标题行一致的读侧 NSFW 兜底，避免活动标题泄漏敏感内容。
                detail_text = ""
                if activity_title:
                    if is_nsfw(activity_app_raw, activity_title):
                        detail_text = f"「{NSFW_MASK_TEXT}」"
                    else:
                        detail_text = f"「{mask_sensitive_text(activity_title, info_blacklist_keywords, info_blacklist_replacement)}」"

                # 多设备时：仅在设备切换处插入分组头，设备组之间用空行隔开。
                if not single_device and activity_device != current_device:
                    current_device = activity_device
                    if lines and lines[-1].strip():
                        lines.append("")
                    if activity_device:
                        lines.append(f"  📱 {activity_device}")

                time_prefix = f"{activity_time} " if activity_time else ""
                lines.append(f"  {index + 1}. {time_prefix}{main_text}{detail_text}")

    # 去除尾部多余空行，保证回复结尾干净。
    while lines and not lines[-1].strip():
        lines.pop()

    rendered = "\n".join(lines)
    logger.debug("[视奸面板] 渲染完成，回复字符数：%s", len(rendered))
    return rendered, len(device_items)


__all__ = [
    "render_dashboard_message_with_count",
    "select_devices_for_render",
    "_is_online",
    "clean_text",
]
