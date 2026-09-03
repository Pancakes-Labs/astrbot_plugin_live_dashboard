"""健康数据消息渲染层。

职责：
- 消费 /api/health-data 返回的 records 数组，按指标类型分组汇总展示。
- 提供心率/步数/睡眠等常见的可读格式化。
- 属纯逻辑，无 IO。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..utils.config_parser import get_int_value
from ..utils.text_utils import clean_text, format_short_time

# 指标类型 → 人类可读名称（中文）。
_TYPE_LABELS: dict[str, str] = {
    "heart_rate": "心率",
    "resting_heart_rate": "静息心率",
    "heart_rate_variability": "心率变异性",
    "steps": "步数",
    "distance": "距离",
    "exercise": "运动",
    "sleep": "睡眠",
    "oxygen_saturation": "血氧",
    "body_temperature": "体温",
    "respiratory_rate": "呼吸频率",
    "blood_pressure": "血压",
    "blood_glucose": "血糖",
    "weight": "体重",
    "height": "身高",
    "active_calories": "活动热量",
    "total_calories": "总热量",
    "hydration": "饮水",
    "nutrition": "营养",
}

# 单位（按指标）。
# 注意：sleep / exercise / distance / steps 等指标由 _format_typed_value
# 按上游存储单位（分钟 / 米 / 次数）单独换算，不在此表定义展示单位。
_TYPE_UNITS: dict[str, str] = {
    "heart_rate": "bpm",
    "resting_heart_rate": "bpm",
    "heart_rate_variability": "ms",
    "oxygen_saturation": "%",
    "body_temperature": "℃",
    "respiratory_rate": "次/分",
    "weight": "kg",
    "height": "cm",
    "active_calories": "kcal",
    "total_calories": "kcal",
    "hydration": "mL",
}


def _format_value(value: Any, unit: str) -> str:
    """值 + 单位格式化。"""
    if isinstance(value, (int, float)):
        # 保留最多两位小数，去掉无意义的结尾 0。
        text = f"{float(value):.2f}".rstrip("0").rstrip(".")
        if text == "-0":
            text = "0"
        return f"{text} {unit}".strip() if unit else text
    if value is None:
        return "—"
    return str(value)


def _format_typed_value(type_name: str, value: Any) -> str:
    """按指标类型格式化值，把上游原始存储单位换算为可读展示单位。

    上游存储约定（与 health-data / health-webhook 一致）：
    - sleep / exercise 以**分钟**存储（Apple 导出 7.5 小时会被存为 450）；
    - distance 以**米**存储（前端展示时换算成 km）；
    - steps 为纯次数，展示时加千分位。
    其余指标按原始值 + _TYPE_UNITS 展示。
    """
    if type_name in ("sleep", "exercise"):
        if not isinstance(value, (int, float)):
            return _format_value(value, "")
        minutes = max(0, float(value))
        hours, remainder = divmod(int(round(minutes)), 60)
        return f"{hours}小时{remainder}分" if hours > 0 else f"{remainder}分"

    if type_name == "distance":
        if not isinstance(value, (int, float)):
            return _format_value(value, "")
        meters = max(0, float(value))
        if meters >= 1000:
            km_text = f"{meters / 1000:.2f}".rstrip("0").rstrip(".")
            return f"{km_text} km"
        return f"{int(meters)} m"

    if type_name == "steps":
        if isinstance(value, (int, float)):
            return f"{int(value):,}"
        return _format_value(value, "")

    return _format_value(value, _TYPE_UNITS.get(type_name, ""))


def render_health_message(
    health_data: dict[str, Any],
    config: dict[str, Any],
    device_names: dict[str, str] | None = None,
) -> str:
    """渲染健康数据文本。

    Args:
        health_data: /api/health-data 返回体。
        config: 插件配置。
        device_names: 可选 device_id → device_name 映射。上游 health-data
            的 records 不含设备名，传入映射后展示友好名称。

    Returns:
        渲染后的文本。
    """
    date = clean_text(health_data.get("date"))
    records_raw = health_data.get("records", [])
    records = (
        [r for r in records_raw if isinstance(r, dict)]
        if isinstance(records_raw, list)
        else []
    )

    if not records:
        return f"📊 Live Dashboard 健康数据（{date or '今日'}）\n\n当日暂无健康数据喵"

    lines: list[str] = [f"❤️ Live Dashboard 健康数据（{date or '今日'}）"]

    # 按设备分组，组内再按指标汇总。
    # 每组只输出关键指标（避免刷屏），其余用总数提示。
    max_records = get_int_value(
        config, "health_max_records", 40, min_value=1, max_value=200
    )

    # 按 device_id 聚合
    by_device: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_device[clean_text(record.get("device_id"))].append(record)

    shown = 0
    for device_id, device_records in by_device.items():
        if shown >= max_records:
            lines.append(f"  … 还有更多数据未展示（上限 {max_records} 条）")
            break

        # 规整设备名：health-data 响应不含 device_name，
        # 优先使用调用方提供的 device_id → name 映射。
        device_name = (
            (device_names or {}).get(device_id)
            or device_records[0].get("device_name")
            or device_id
        )
        lines.append("")
        lines.append(f"• {device_name}")

        # 按指标名分组
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in device_records:
            by_type[clean_text(record.get("type"))].append(record)

        for type_name, type_records in by_type.items():
            if shown >= max_records:
                lines.append(f"  … 还有更多数据未展示（上限 {max_records} 条）")
                break

            label = _TYPE_LABELS.get(type_name, type_name)
            # 最新一条 + 是否有多条（数值按上游原始存储单位换算展示）
            latest = type_records[0]
            latest_text = _format_typed_value(type_name, latest.get("value"))
            if len(type_records) > 1:
                lines.append(
                    f"  {label}：{latest_text}（共 {len(type_records)} 条，最新 {format_short_time(clean_text(latest.get('recorded_at')))}）"
                )
            else:
                lines.append(f"  {label}：{latest_text}")
            shown += 1

    return "\n".join(lines)


__all__ = ["render_health_message"]
