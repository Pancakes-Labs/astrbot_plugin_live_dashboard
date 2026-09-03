"""启动横幅生成器。

负责在插件加载时打印组织名 Pancakes-Labs 的 ASCII art 横幅（bold_cyan 配色，
带框线），艺术字下方的插件名、版本与简介水平居中，底部附版权声明
（起始年份固定 2026，结束年份动态取当前年份）。

排版说明：
- 面板统一使用窄宽度（默认 60 列）框线，减少留白；
- 使用 _display_width() 基于 unicodedata.east_asian_width() 精确估算显示宽度，
  中英/emoji 混排时右侧框线也能严格对齐；
- 使用 shutil.get_terminal_size() 探测终端宽度，宽度不足时 Pancakes 与 Labs
  自动换行显示，避免被终端折行破坏等宽效果。

颜色说明：
- 仅当终端支持 ANSI 颜色（stdout 为 TTY 且非 NO_COLOR 环境）时启用 bold_cyan；
- 否则回退为纯文本，保证日志文件与不支持彩色的终端下依然可读。
"""

from __future__ import annotations

import os
import shutil
import sys
import unicodedata
from datetime import datetime

from astrbot.api import logger

from .version import get_plugin_version

# ---------------------------------------------------------------------------
# Pancakes-Labs ASCII art（等宽字符，bold_cyan 配色）
# ---------------------------------------------------------------------------
_ASCII_ART_PANCAKES = r"""██████╗  █████╗ ███╗   ██╗ ██████╗ █████╗ ██╗  ██╗███████╗███████╗
██╔══██╗██╔══██╗████╗  ██║██╔════╝██╔══██╗██║ ██╔╝██╔════╝██╔════╝
██████╔╝███████║██╔██╗ ██║██║     ███████║█████╔╝ █████╗  ███████╗█████╗
██╔═══╝ ██╔══██║██║╚██╗██║██║     ██╔══██║██╔═██╗ ██╔══╝  ╚════██║╚════╝
██║     ██║  ██║██║ ╚████║╚██████╗██║  ██║██║  ██╗███████╗███████║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝"""

_ASCII_ART_LABS = r"""██╗      █████╗ ██████╗ ███████╗
██║     ██╔══██╗██╔══██╗██╔════╝
██║     ███████║██████╔╝███████╗
██║     ██╔══██║██╔══██╗╚════██║
███████╗██║  ██║██████╔╝███████║
╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝"""


# ---------------------------------------------------------------------------
# 面板框线字符
# ---------------------------------------------------------------------------
_PANEL_TOP = "┌"
_PANEL_TOP_RIGHT = "┐"
_PANEL_BOTTOM = "└"
_PANEL_BOTTOM_RIGHT = "┘"
_PANEL_HORIZONTAL = "─"
_PANEL_VERTICAL = "│"
_PANEL_TITLE_LEFT = "┤"
_PANEL_TITLE_RIGHT = "├"


# ---------------------------------------------------------------------------
# ANSI 颜色工具
# ---------------------------------------------------------------------------
_ANSI_BOLD_CYAN = "\x1b[1;36m"
_ANSI_RESET = "\x1b[0m"


def _supports_color() -> bool:
    """是否启用 ANSI 颜色：stdout 为 TTY 且未显式禁用颜色。"""
    if os.environ.get("NO_COLOR"):
        return False
    try:
        stream = getattr(sys, "stdout", None)
        return bool(stream is not None and stream.isatty())
    except Exception:
        return False


def _paint_bold_cyan(text: str) -> str:
    """用 bold_cyan 着色（若终端不支持颜色则原样返回）。"""
    if not _supports_color():
        return text
    return f"{_ANSI_BOLD_CYAN}{text}{_ANSI_RESET}"


# ---------------------------------------------------------------------------
# 终端宽度探测
# ---------------------------------------------------------------------------
def _terminal_width() -> int:
    try:
        size = shutil.get_terminal_size(fallback=(80, 24))
        return int(size.columns)
    except Exception:
        return 80


# ---------------------------------------------------------------------------
# 宽度与居中工具
# ---------------------------------------------------------------------------
def _display_width(text: str) -> int:
    """估算字符串在终端的显示宽度（中英混排右线对齐的正解）。

    使用 unicodedata.east_asian_width() 判断：
    - "W" / "F"（全角/宽）→ 2 列
    - 其余（含 "A" 模糊宽度，如块字符 █╗、· 等）→ 1 列
      在等宽终端里这些字符均占 1 列，按 2 计会高估宽度导致右线错开。
    - 零宽字符（ZWJ U+200D、变体选择符 U+FE00~FE0F）→ 0 列
    - 后随变体选择符 U+FE0F 的字符按 emoji 呈现、占 2 列，
      避免 EAW 为 "N" 的基础字符（如时钟类符号）被低估为 1 列。
    """
    width = 0
    for i, ch in enumerate(text):
        code = ord(ch)
        # 零宽字符（ZWJ U+200D、变体选择符 U+FE00~FE0F）不占列宽
        if code == 0x200D or 0xFE00 <= code <= 0xFE0F:
            continue
        base = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        # 后随 FE0F 的字符按 emoji 渲染（2 列）
        if base == 1 and i + 1 < len(text) and ord(text[i + 1]) == 0xFE0F:
            base = 2
        width += base
    return width


def _pad(text: str, width: int) -> str:
    """按显示宽度补齐到指定宽度（半角占 1，全角/emoji 占 2）。"""
    return text + " " * max(0, width - _display_width(text))


def _center(text: str, width: int) -> str:
    """按显示宽度水平居中，左补 1 格保持视觉平衡。"""
    pad_total = max(0, width - _display_width(text))
    left = pad_total // 2
    right = pad_total - left
    return " " * left + text + " " * right


# ---------------------------------------------------------------------------
# ASCII art 生成（含宽度自适应）
# ---------------------------------------------------------------------------
def build_banner_lines() -> list[str]:
    """生成带边框的横幅文本行（未着色），供打印与测试使用。"""
    width = _terminal_width()
    pancakes_lines = _ASCII_ART_PANCAKES.splitlines()
    labs_lines = _ASCII_ART_LABS.splitlines()

    # 单行并排所需的最小列数：取 Pancakes 行最大宽 + 1 空格 + Labs 行最大宽
    max_pancakes_width = max(len(line) for line in pancakes_lines)
    max_labs_width = max(len(line) for line in labs_lines)
    single_line_width = max_pancakes_width + 1 + max_labs_width

    # 宽度充足（>= 单行所需）时单行并排，否则 Labs 换行。
    # 注意：Pancakes 各行宽度不一（第 3/4 行含额外块字符），
    # 必须按最大宽度 ljust 补齐后再拼接，否则 Labs 列会对不齐。
    if width >= single_line_width:
        art_lines: list[str] = []
        for p, lab in zip(pancakes_lines, labs_lines):
            art_lines.append(f"{p.ljust(max_pancakes_width)} {lab}")
    else:
        art_lines = list(pancakes_lines) + list(labs_lines)

    # 计算整个横幅的显示宽度（取 art 行最大宽 + 两侧留白 + 边框竖线）
    art_width = max(_display_width(line) for line in art_lines)
    inner_width = art_width + 4  # 左右各留 2 空格

    version = (get_plugin_version() or "").strip()

    # 版权年份区间：起始年份固定为 2026，结束年份动态取当前年份；
    # 当年份恰为 2026 时只显示单一年份，避免出现 "2026-2026"。
    current_year = datetime.now().year
    copyright_years = f"2026-{current_year}" if current_year > 2026 else "2026"

    caption_lines = [
        f"Live Dashboard Plugin  ·  {version}",
        "AstrBot 视奸面板插件 · 设备状态 / 时间线 / 健康数据",
        f"Copyright © {copyright_years}",
        "DBJD-CR & 🥞Pancakes-Labs. All Rights Reserved.",
    ]

    lines: list[str] = []
    lines.append(_PANEL_TOP + _PANEL_HORIZONTAL * inner_width + _PANEL_TOP_RIGHT)
    for art in art_lines:
        lines.append(
            f"{_PANEL_VERTICAL}  {_pad(art, inner_width - 4)}  {_PANEL_VERTICAL}"
        )
    lines.append(
        _PANEL_TITLE_RIGHT + _PANEL_HORIZONTAL * inner_width + _PANEL_TITLE_LEFT
    )
    for cap in caption_lines[:2]:
        lines.append(
            f"{_PANEL_VERTICAL} {_center(cap, inner_width - 2)} {_PANEL_VERTICAL}"
        )
    # 版权信息与上方插件说明之间单独画一条分隔线
    lines.append(
        _PANEL_TITLE_RIGHT + _PANEL_HORIZONTAL * inner_width + _PANEL_TITLE_LEFT
    )
    for cap in caption_lines[2:]:
        lines.append(
            f"{_PANEL_VERTICAL} {_center(cap, inner_width - 2)} {_PANEL_VERTICAL}"
        )
    lines.append(_PANEL_BOTTOM + _PANEL_HORIZONTAL * inner_width + _PANEL_BOTTOM_RIGHT)
    return lines


def print_banner() -> None:
    """打印 Pancakes-Labs ASCII art 横幅（bold_cyan 配色，带边框，说明居中）。"""
    for line in build_banner_lines():
        logger.info(_paint_bold_cyan(line))


__all__ = ["build_banner_lines", "print_banner"]
