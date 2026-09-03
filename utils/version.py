"""版本信息辅助工具。

负责读取插件版本与 AstrBot 版本，供状态展示、启动横幅与遥测上报等场景复用。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import metadata as importlib_metadata
from pathlib import Path

# 优先使用标准库 tomllib；若运行环境较旧，则回退到 tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

import astrbot
from astrbot.api import logger


@dataclass(frozen=True)
class AstrBotVersionInfo:
    """AstrBot 版本探测结果。"""

    version: str
    source: str
    error: str | None = None


def get_plugin_version() -> str:
    """获取插件版本号（metadata.yaml 的 version 字段）。

    读取失败或字段缺失时回退为 "unknown"，保证调用方无需关心异常。
    """
    try:
        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        metadata_path = os.path.join(plugin_root, "metadata.yaml")
        if os.path.exists(metadata_path):
            with open(metadata_path, encoding="utf-8") as f:
                for line in f:
                    match = re.match(r"^\s*version:\s*([^#\n]+)", line)
                    if match:
                        return match.group(1).strip()
    except Exception as exc:
        logger.debug("[视奸面板] 获取插件版本失败: %s", exc)

    return "unknown"


def get_plugin_name() -> str:
    """获取插件名（metadata.yaml 的 name 字段）。"""
    plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        metadata_path = os.path.join(plugin_root, "metadata.yaml")
        if os.path.exists(metadata_path):
            with open(metadata_path, encoding="utf-8") as f:
                for line in f:
                    match = re.match(r"^\s*name:\s*([^#\n]+)", line)
                    if match:
                        return match.group(1).strip()
    except Exception as exc:
        logger.debug("[视奸面板] 获取插件名失败: %s", exc)

    try:
        if plugin_root and os.path.basename(plugin_root):
            return os.path.basename(plugin_root)
    except Exception:
        pass

    return "astrbot_plugin_live_dashboard"


def _build_unknown_version_info(
    default: str = "unknown",
    error: str = "all_methods_failed",
) -> AstrBotVersionInfo:
    """构造未知版本探测结果。"""
    return AstrBotVersionInfo(version=default, source="unknown", error=error)


def _get_astrbot_version_from_core_config() -> AstrBotVersionInfo | None:
    """优先从 AstrBot 运行时核心配置模块读取版本。"""
    module_candidates = (
        "astrbot.core.config",
        "astrbot.core.config.default",
    )

    for module_name in module_candidates:
        try:
            module = __import__(module_name, fromlist=["VERSION"])
            version = str(getattr(module, "VERSION", "")).strip()
            if version:
                return AstrBotVersionInfo(version=version, source="core_config")
        except Exception as exc:
            logger.debug(
                "[视奸面板] 从 %s 读取 AstrBot VERSION 失败: %s", module_name, exc
            )

    return None


def _get_astrbot_version_from_distribution() -> AstrBotVersionInfo | None:
    """从 AstrBot 安装分发元数据读取版本。"""
    for dist_name in ("AstrBot", "astrbot"):
        try:
            version = str(importlib_metadata.version(dist_name)).strip()
            if version:
                return AstrBotVersionInfo(version=version, source="distribution")
        except importlib_metadata.PackageNotFoundError:
            pass
        except Exception as exc:
            logger.debug(
                "[视奸面板] 读取 AstrBot 分发元数据失败 (%s): %s", dist_name, exc
            )

    return None


def _get_astrbot_version_from_cli_module() -> AstrBotVersionInfo | None:
    """从 AstrBot CLI 模块常量读取版本。"""
    try:
        from astrbot.cli import __version__ as cli_version

        version = str(cli_version).strip()
        if version:
            return AstrBotVersionInfo(version=version, source="cli_module")
    except Exception as exc:
        logger.debug("[视奸面板] 导入 astrbot.cli.__version__ 失败: %s", exc)

    return None


def _get_astrbot_version_from_pyproject(default: str = "unknown") -> AstrBotVersionInfo:
    """从 AstrBot 安装目录附近的 pyproject.toml 中兜底读取版本。"""
    try:
        astrbot_path = Path(astrbot.__file__).resolve().parent.parent
        pyproject_path = astrbot_path / "pyproject.toml"

        if not pyproject_path.exists():
            return _build_unknown_version_info(default, "pyproject_missing")

        if tomllib is None:
            return _build_unknown_version_info(default, "tomllib_unavailable")

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        project_version = str(data.get("project", {}).get("version", "")).strip()
        if project_version:
            return AstrBotVersionInfo(version=project_version, source="pyproject")

        poetry_version = str(
            data.get("tool", {}).get("poetry", {}).get("version", "")
        ).strip()
        if poetry_version:
            return AstrBotVersionInfo(version=poetry_version, source="pyproject")

        return _build_unknown_version_info(default, "pyproject_version_missing")
    except Exception as exc:
        logger.debug("[视奸面板] 解析 AstrBot pyproject.toml 失败: %s", exc)
        return _build_unknown_version_info(default, "pyproject_parse_failed")


@lru_cache(maxsize=8)
def get_astrbot_version_info(default: str = "unknown") -> AstrBotVersionInfo:
    """获取带来源与错误码的 AstrBot 版本探测结果。"""
    for resolver in (
        _get_astrbot_version_from_core_config,
        _get_astrbot_version_from_distribution,
        _get_astrbot_version_from_cli_module,
    ):
        version_info = resolver()
        if version_info is not None:
            return version_info

    return _get_astrbot_version_from_pyproject(default)


def get_astrbot_version(default: str = "unknown") -> str:
    """获取 AstrBot 版本号字符串。"""
    return get_astrbot_version_info(default).version


__all__ = [
    "AstrBotVersionInfo",
    "get_plugin_version",
    "get_plugin_name",
    "get_astrbot_version_info",
    "get_astrbot_version",
]
