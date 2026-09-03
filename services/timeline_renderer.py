"""时间线消息渲染层。

职责：
- 消费 /api/timeline 返回的 segments（分段时间轴）与 summary（按应用/设备汇总）。
- 文案优先生成「今日时间长流」，并按应用汇总时长。
- 属纯逻辑，不含 IO；任何异常在 service 层兜底。
"""

from __future__ import annotations

import re
from typing import Any

from ..utils.config_parser import (
    get_bool_value,
    get_int_value,
    get_text_value,
    parse_list_config,
)
from ..utils.nsfw_filter import is_nsfw
from ..utils.text_utils import (
    NSFW_MASK_TEXT,
    clean_text,
    format_short_time,
    mask_sensitive_text,
)

# display_title 超长时截断，避免单行刷屏（与状态面板对齐）。
_MAX_TITLE_LENGTH = 120

# 常见标题尾缀「和另外 N 个页面」→ 压缩为 +N（减少行宽占用）。
_TITLE_PAGE_TAIL_SUFFIX = re.compile(r"和另外\s*(\d+)\s*个页面$")


def render_timeline_message(
    timeline_data: dict[str, Any],
    config: dict[str, Any],
) -> tuple[str, int]:
    """渲染时间线文本。

    Returns:
        (渲染文本, 段数) —— 段数为 0 表示无数据或全部被过滤。
    """
    date = clean_text(timeline_data.get("date"))
    segments_raw = timeline_data.get("segments", [])
    segments = (
        [s for s in segments_raw if isinstance(s, dict)]
        if isinstance(segments_raw, list)
        else []
    )
    summary_raw = timeline_data.get("summary", {})
    summary = summary_raw if isinstance(summary_raw, dict) else {}

    # summary 的键是 device_id，而 segments 里带有友好 device_name。
    # 建立映射后汇总区展示设备名而非原始 id。
    device_name_map: dict[str, str] = {}
    for segment in segments:
        did = clean_text(segment.get("device_id"))
        dname = clean_text(segment.get("device_name"))
        if did and dname and did not in device_name_map:
            device_name_map[did] = dname

    # 数量限制，避免刷屏。
    max_segments = get_int_value(
        config, "timeline_max_segments", 40, min_value=1, max_value=200
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

    # 展示设备名开关（与状态面板对齐）。
    show_device_names = get_bool_value(config, "timeline_show_device_names", True)

    today_text = date or "今日"
    lines: list[str] = [
        f"📜 Live Dashboard 时间线（{today_text}）",
    ]

    # 判断是否单设备：summary 与 segments 中出现的设备取并集，去重后仅 1 台则上浮设备名。
    summary_device_ids = {str(did) for did in summary.keys() if str(did)}
    segment_device_ids = {
        clean_text(seg.get("device_id")) for seg in segments if seg.get("device_id")
    }
    all_device_ids = summary_device_ids | segment_device_ids
    single_device = len(all_device_ids) == 1

    # ── summary 区：设备名上浮 / 分组 ──────────────────────────────
    if summary:
        lines.append("")
        if single_device:
            only_id = next(iter(summary_device_ids)) if summary_device_ids else ""
            only_name = device_name_map.get(only_id, only_id)
            title = (
                f"各应用累计时长（{only_name}）："
                if show_device_names and only_name
                else "各应用累计时长："
            )
            lines.append(title)
            app_items = sorted(
                next(iter(summary.values())).items(),
                key=lambda kv: kv[1],
                reverse=True,
            )
            for app_name, minutes in app_items:
                display = mask_sensitive_text(
                    clean_text(app_name),
                    info_blacklist_keywords,
                    info_blacklist_replacement,
                )
                lines.append(f"  {display}：{_format_duration(minutes)}")
        else:
            lines.append("各应用累计时长：")
            for device_id, app_map in summary.items():
                display_device = device_name_map.get(str(device_id), str(device_id))
                if show_device_names and display_device:
                    lines.append(f"  📱 {display_device}")
                app_items = sorted(app_map.items(), key=lambda kv: kv[1], reverse=True)
                for app_name, minutes in app_items:
                    display = mask_sensitive_text(
                        clean_text(app_name),
                        info_blacklist_keywords,
                        info_blacklist_replacement,
                    )
                    lines.append(f"    {display}：{_format_duration(minutes)}")

    if not segments:
        lines.append("")
        lines.append("当天暂无活动记录喵。")
        return "\n".join(lines), 0

    # ── 片段区：设备分组 + 相邻重复合并 + 标题精简 ────────────────
    lines.append("")
    if single_device:
        only_id = next(iter(segment_device_ids)) if segment_device_ids else ""
        only_name = device_name_map.get(only_id, only_id)
        seg_title = (
            f"时间线片段（{only_name}）："
            if show_device_names and only_name
            else "时间线片段："
        )
        lines.append(seg_title)
    else:
        lines.append("时间线片段：")

    shown = 0
    # current_group_device：当前遍历片段所属设备（多设备分组用）。
    # current_bucket：当前合并桶（应用+动作+标题+设备 相同则合并）。
    current_bucket: dict | None = None
    current_group_device: str | None = None

    for segment in segments:
        app_name = clean_text(segment.get("app_name"))
        display_title = clean_text(segment.get("display_title"))
        status_text = clean_text(segment.get("status_text"))
        started_at = clean_text(segment.get("started_at"))
        duration_minutes = segment.get("duration_minutes")
        device_id = clean_text(segment.get("device_id"))
        device_name = clean_text(segment.get("device_name"))

        if not app_name and not display_title and not status_text:
            continue

        start_text = format_short_time(started_at) if started_at else "?"

        display_name = mask_sensitive_text(
            status_text or app_name, info_blacklist_keywords, info_blacklist_replacement
        )

        # 标题精简：压缩尾缀并截断超长标题。
        title_part = ""
        if display_title:
            if is_nsfw(app_name, display_title):
                title_part = f"「{NSFW_MASK_TEXT}」"
            else:
                cleaned_title = mask_sensitive_text(
                    clean_text(display_title),
                    info_blacklist_keywords,
                    info_blacklist_replacement,
                )
                title_part = f"「{_shorten_title(cleaned_title)}」"

        # 合并键：同一设备 + 同样叙事 + 同样标题。
        bucket_key = (device_id, display_name, title_part)
        if (
            current_bucket
            and current_bucket["key"] == bucket_key
            and current_bucket["device_id"] == device_id
        ):
            current_bucket["end_text"] = start_text
            current_bucket["count"] += 1
            current_bucket["duration_total"] += duration_minutes or 0
            continue

        # 新桶（或设备切换）：先落盘旧桶。
        if current_bucket is not None:
            _append_bucket_line(lines, current_bucket)
            shown += 1

        current_bucket = None

        # 已达展示上限，不再开新桶。
        if shown >= max_segments:
            lines.append(f"  … 还有更多片段未展示（上限 {max_segments} 条）")
            break

        # 多设备分组：仅当设备切换时插入设备头（含空行）。
        if not single_device and device_name != current_group_device:
            current_group_device = device_name
            if lines and lines[-1].strip():
                lines.append("")
            if show_device_names and device_name:
                lines.append(f"  📱 {device_name}")

        # 开新桶。
        current_bucket = {
            "key": bucket_key,
            "device_id": device_id,
            "display_name": display_name,
            "title_part": title_part,
            "start_text": start_text,
            "end_text": start_text,
            "count": 1,
            "duration_total": duration_minutes or 0,
        }

    # 落盘最后一个桶（未触发上限 break 时）。
    if current_bucket is not None and shown < max_segments:
        _append_bucket_line(lines, current_bucket)
        shown += 1

    return "\n".join(lines), shown


def _format_duration(minutes: int) -> str:
    """把分钟数格式化为可读时长。

    规则：
    - 0 分钟显示「小于1分钟」，避免出现（0分）这类观感不佳的文案；
    - 不足 1 小时显示「N分钟」；
    - 满 1 小时显示「N小时M分钟」，M 为 0 时也保留「0分钟」部分。
    """
    minutes = max(0, int(minutes))
    if minutes <= 0:
        return "小于1分钟"
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}小时{mins}分钟"
    return f"{mins}分钟"


def _shorten_title(title: str) -> str:
    """精简 display_title：压缩「和另外 N 个页面」尾缀，并截断超长标题。"""
    if not title:
        return title
    short = _TITLE_PAGE_TAIL_SUFFIX.sub(lambda m: f"+{m.group(1)}", title)
    if len(short) > _MAX_TITLE_LENGTH:
        short = short[: _MAX_TITLE_LENGTH - 1].rstrip() + "…"
    return short


def _append_bucket_line(lines: list[str], bucket: dict) -> None:
    """把合并桶输出为一行时间线文本。

    时间区间：单条只显示起始时间，多条合并显示「起始~结束」。
    多条合并附 ×N 次数；有累计时长时追加（N分钟）。
    """
    time_range = (
        f"{bucket['start_text']}~{bucket['end_text']}"
        if bucket["count"] > 1
        else bucket["start_text"]
    )
    body = f"  {time_range} {bucket['display_name']}{bucket['title_part']}"
    if bucket["count"] > 1:
        body += f" ×{bucket['count']}"
    if bucket["duration_total"]:
        body += f"（{_format_duration(bucket['duration_total'])}）"
    lines.append(body)


__all__ = ["render_timeline_message"]
