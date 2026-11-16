#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir 动态日报 · 抓取模块
5 个源，统一输出为 [{title, url, summary, pub, source}] 结构。
"""

import os
import re
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import requests

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0"

# ── 源清单（实测可用，详见 docs/01-信息源规格.md）────────────────────────────
SOURCES = [
    ("Palantir 官方博客", "https://blog.palantir.com/feed"),
    ("TechCrunch Palantir", "https://techcrunch.com/tag/palantir/feed/"),
    ("AIHOT 精选", "https://aihot.virxact.com/rss"),
    ("Google News Palantir",
     "https://news.google.com/rss/search?q=Palantir&hl=en-US&gl=US&ceid=US:en"),
    ("Google News Alex Karp",
     "https://news.google.com/rss/search?q=%22Alex+Karp%22&hl=en-US&gl=US&ceid=US:en"),
]

# Palantir 是低频公司：官方博客最新一篇可能在一个月前，TechCrunch 也可能两周没更新。
# 窗口太窄会把最有价值的源全滤掉，所以放宽到 30 天，靠 last_sent 去重库避免重复报旧闻。
FRESH_DAYS = 30
PER_SOURCE_MAX = 20  # 每源最多取几条


def _localname(tag):
    """去掉 XML 命名空间，兼容 RSS 与 Atom。"""
    return tag.split("}")[-1] if "}" in tag else tag


def _clean_html(text):
    """剥离 HTML 标签，压缩空白。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(raw):
    """解析 RSS/Atom 的各种时间格式，失败返回 None。"""
    if not raw:
        return None
    raw = raw.strip()
    # RFC 2822（RSS 的 pubDate）
    try:
        return parsedate_to_datetime(raw)
    except Exception:
        pass
    # ISO 8601（Atom 的 published/updated）
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw.replace("Z", "+0000"), fmt)
        except Exception:
            continue
    return None


def _get_child(elem, *names):
    """按 localname 取子元素的文本，支持多个候选标签名。"""
    for child in elem:
        if _localname(child.tag) in names:
            return (child.text or "").strip()
    return ""


def _get_link(elem):
    """取链接。RSS 是 <link>文本</link>，Atom 是 <link href="..."/>。"""
    for child in elem:
        if _localname(child.tag) == "link":
            href = (child.get("href") or "").strip()
            if href:
                return href
            if child.text and child.text.strip():
                return child.text.strip()
    return ""


def fetch_rss(source_name, url):
    """抓取并解析单个 RSS/Atom 源。"""
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        # 同时兼容 <item>（RSS）和 <entry>（Atom）
        entries = [e for e in root.iter() if _localname(e.tag) in ("item", "entry")]
        results = []

        for e in entries[:PER_SOURCE_MAX]:
            title = _clean_html(_get_child(e, "title"))
            link = _get_link(e)
            desc = _clean_html(_get_child(e, "description", "summary", "content"))
            pub_raw = _get_child(e, "pubDate", "published", "updated")

            if not title or not link:
                continue

            pub_dt = _parse_date(pub_raw)
            results.append({
                "title": title,
                "url": link,
                "summary": desc[:500],
                "pub": pub_dt,
                "source": source_name,
            })

        log.info(f"[{source_name}] 抓到 {len(results)} 条")
        return results

    except Exception as e:
        log.warning(f"[{source_name}] 抓取失败: {str(e)[:100]}")
        return []


def is_palantir_related(item):
    """
    判断一条是否与 Palantir 相关。

    官方博客和 TechCrunch 标签页天然就是 Palantir 内容，直接放行。
    AIHOT 是通用 AI 新闻聚合，必须筛——否则 15 条全是 Qwen/Anthropic 的噪音。
    Google News 的查询词已含 Palantir/Alex Karp，但结果里仍可能混入无关文章。
    """
    # 天然相关的源，不筛
    if item["source"] in ("Palantir 官方博客", "TechCrunch Palantir"):
        return True

    blob = (item["title"] + " " + item["summary"]).lower()
    if "palantir" in blob or "pltr" in blob:
        return True

    # Alex Karp 是 Palantir CEO，提到他基本就是在说 Palantir
    if "karp" in blob:
        return True

    # Foundry / AIP / Apollo 三个产品线名，注意避免误伤：
    # "foundry" 在半导体语境指晶圆厂，"apollo" 可能是其他项目名，
    # 所以这两个词要和其他 Palantir 信号共现才算（这里用"含公司名"已经覆盖，故不放宽）
    return False


def fetch_all():
    """抓取所有源，去重后按时间过滤。"""
    all_items = []
    for name, url in SOURCES:
        all_items.extend(fetch_rss(name, url))

    # URL 去重
    seen = set()
    unique = []
    for it in all_items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        unique.append(it)

    # Palantir 相关性过滤（AIHOT 是通用 AI 新闻，必须筛）
    relevant = [it for it in unique if is_palantir_related(it)]
    dropped_irrelevant = len(unique) - len(relevant)
    if dropped_irrelevant:
        log.info(f"相关性过滤丢弃 {dropped_irrelevant} 条非 Palantir 内容")

    # 时间过滤（无时间的保留，交由下游判断）
    cutoff = datetime.now().astimezone() - timedelta(days=FRESH_DAYS)
    fresh = []
    dropped_old = 0
    for it in relevant:
        if it["pub"] is None:
            fresh.append(it)  # 无时间不丢，可能是解析失败
            continue
        pub = it["pub"]
        if pub.tzinfo is None:
            pub = pub.astimezone()
        if pub >= cutoff:
            fresh.append(it)
        else:
            dropped_old += 1

    log.info(f"合计 {len(all_items)} 条 → 去重后 {len(unique)} 条 → "
             f"相关 {len(relevant)} 条 → 时间过滤丢 {dropped_old} 条 "
             f"→ 最终 {len(fresh)} 条")
    return fresh


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    items = fetch_all()
    print(f"\n{'='*60}")
    for it in items:
        pub = it["pub"].strftime("%m-%d %H:%M") if it["pub"] else "无时间"
        print(f"[{it['source']}] {pub}")
        print(f"  {it['title'][:80]}")
        print(f"  {it['url'][:90]}")
