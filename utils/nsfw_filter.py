"""读侧 NSFW 过滤器（纯逻辑，无 IO）。

背景：
- 上游写侧（report.ts）会基于 nsfw-blocklist.json 静默丢弃 NSFW 内容，
  但读侧不保证历史数据已被清洗（升级前入库的数据仍在）。
- 插件在渲染层追加一道读侧过滤：命中即整体打码，避免泄露到群里。

实现：
- 内嵌上游 nsfw-blocklist.json 的域名 / 关键词 / app_id 黑名单。
- 域名匹配支持剥掉 www./m. 前缀与子域名后缀匹配。
"""

from __future__ import annotations

import re

# ── 数据源：复刻上游 packages/backend/src/data/nsfw-blocklist.json ──

_BLOCKED_DOMAINS = frozenset(
    {
        "pornhub.com",
        "xvideos.com",
        "xhamster.com",
        "xnxx.com",
        "redtube.com",
        "youporn.com",
        "tube8.com",
        "spankbang.com",
        "eporner.com",
        "tnaflix.com",
        "nhentai.net",
        "hanime.tv",
        "hentaihaven.xxx",
        "rule34.xxx",
        "e-hentai.org",
        "exhentai.org",
        "gelbooru.com",
        "danbooru.donmai.us",
        "hitomi.la",
        "javbus.com",
        "javdb.com",
        "avgle.com",
        "missav.com",
        "thisav.com",
        "jable.tv",
        "91porn.com",
        "sex.com",
        "chaturbate.com",
        "stripchat.com",
        "cam4.com",
        "bongacams.com",
        "onlyfans.com",
        "fansly.com",
        "iwara.tv",
    }
)

_BLOCKED_KEYWORDS = frozenset(
    {
        "pornhub",
        "xvideos",
        "xhamster",
        "nhentai",
        "hentai",
        "hanime",
        "rule34",
        "e-hentai",
        "exhentai",
        "gelbooru",
        "danbooru",
        "javbus",
        "javdb",
        "missav",
        "91porn",
        "onlyfans",
        "fansly",
        "chaturbate",
        "stripchat",
    }
)

_BLOCKED_APP_IDS = frozenset(
    {
        "com.pornhub.android",
        "com.xvideos.app",
        "com.xhamster.app",
    }
)

# 匹配文本中疑似域名的片段（与上游 extractDomains 语义一致）。
_DOMAIN_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?([a-z0-9][-a-z0-9]*(?:\.[a-z0-9][-a-z0-9]*)+)",
    re.IGNORECASE,
)


def _extract_domains(text: str) -> list[str]:
    """从文本中提取去前缀后的域名列表。"""
    domains: list[str] = []
    for match in _DOMAIN_PATTERN.findall(text):
        cleaned = match.lower().split("/")[0]
        if cleaned:
            domains.append(cleaned)
    return domains


def is_nsfw(app_id: str, window_title: str) -> bool:
    """判断应用 ID 与标题组合是否命中 NSFW 黑名单。

    Args:
        app_id: 上游上报的 app_id（如包名 / 进程名 / 应用名）。
        window_title: 原始窗口标题（读侧场景可用 display_title 近似）。
    """
    lower_app_id = (app_id or "").strip().lower()
    lower_title = (window_title or "").strip().lower()

    if lower_app_id in _BLOCKED_APP_IDS:
        return True

    # 域名匹配：同时对 app_id 与 title 检查，支持剥 www./m. 前缀，且命中黑名单域名的子域名。
    for text in (lower_app_id, lower_title):
        if not text:
            continue
        for domain in _extract_domains(text):
            if domain in _BLOCKED_DOMAINS:
                return True
            if any(domain.endswith(f".{blocked}") for blocked in _BLOCKED_DOMAINS):
                return True

    # 关键词子串匹配：同时覆盖 app_id 与 title。
    for keyword in _BLOCKED_KEYWORDS:
        if keyword in lower_app_id or keyword in lower_title:
            return True

    return False


__all__ = ["is_nsfw"]
