#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir AIP 产品洞察 · 多渠道深度内容抓取模块
核心逻辑：
  1. 不做 30 天时间一刀切（产品机制、Ontology 架构、企业落地案例跨年不过期）
  2. 聚焦 5 类高质量产品拆解源：
     - 中文深度专栏与开源研究（GitHub palantir-aip-study 全文 + 中文架构搜索）
     - 推特 (X) 核心产品与架构师解读（@PalantirTech / @chadwahl / @PalantirVision，经 Jina 抓取）
     - 技术社区长文（Dev.to #palantir / Medium #palantir / HackerNews Algolia OAG & Ontology）
     - Palantir 官方工程博客（blog.palantir.com/feed）
     - Palantir AIP 官方文档核心专题（Agent Stack / Markings 权限 / Observability 等 15 个模块）
  3. 代码级硬过滤（is_noise）：直接剔除纯股价/财报指标炒作、政治选举口水、招聘贴
"""

import re
import logging
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

# ── 1. RSS / Atom 深度源（不限时间，排除股票词）──────────────────────────────
RSS_SOURCES = [
    ("Palantir 官方工程博客", "https://blog.palantir.com/feed"),
    ("Dev.to Palantir 技术专栏", "https://dev.to/feed/tag/palantir"),
    ("Medium Palantir 深度专栏", "https://medium.com/feed/tag/palantir"),
    (
        "中文 Palantir AIP 架构搜索",
        "https://news.google.com/rss/search?q=Palantir+AIP+%E6%9E%B6%E6%9E%84+OR+Ontology+OR+%E4%BA%A7%E5%93%81+OR+Agent&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    ),
    (
        "英文 AIP & Ontology 机制搜索",
        "https://news.google.com/rss/search?q=%22Palantir+AIP%22+Ontology+OR+%22AIP+Logic%22+OR+workflow+OR+agent+-stock+-NASDAQ+-NYSE+-shares&hl=en-US&gl=US&ceid=US:en",
    ),
]

# ── 2. 推特 (X) 官方与第三方实战账号（通过 r.jina.ai 渲染抓取产品拆解）──────────
X_ACCOUNTS = [
    ("X @PalantirTech (官方产品与DevCon动态)", "PalantirTech"),
    ("X @chadwahl (Palantir Ontology架构师)", "chadwahl"),
    ("X @PalantirVision (AIP与MCP第三方拆解)", "PalantirVision"),
]

# ── 2.5 YouTube 中英文第三方科普、架构拆解与实操教程搜索 ────────────────────────
YOUTUBE_SEARCH_QUERIES = [
    ("YouTube 中文科普与架构拆解", "Palantir+本体论+OR+AIP+架构+OR+产品解析", "zh-CN,zh;q=0.9,en;q=0.8"),
    ("YouTube 英文第三方实操与架构科普", "Palantir+AIP+Ontology+tutorial+OR+explained+OR+workflow", "en-US,en;q=0.9"),
]

# ── 3. GitHub 开源 Palantir AIP 中文深度研究专题（可直接拉取 Raw Markdown）────
GITHUB_STUDY_CHAPTERS = [
    (
        "Palantir AIP 与 Ontology 深度拆解：数字孪生与语义操作层",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/01-palantir-aip-ontology.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/01-palantir-aip-ontology.md",
    ),
    (
        "Palantir FDE（前线部署工程师）模式与产品演进机制解析",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/02-fde-forward-deployed-engineer.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/02-fde-forward-deployed-engineer.md",
    ),
    (
        "Palantir 企业级 AI 落地范式：从数据融合到业务流闭环",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/03-enterprise-ai-landing.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/03-enterprise-ai-landing.md",
    ),
    (
        "国产 AI 平台借鉴 Palantir AIP 的产品设计与落地行动指南",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/04-action-guide-domestic-ai.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/04-action-guide-domestic-ai.md",
    ),
    (
        "Palantir Ontology 工程设计模式：对象、关系与 Action Types 建模实践",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/05-ontology-engineering-patterns.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/05-ontology-engineering-patterns.md",
    ),
    (
        "语义运行时对比：Palantir Ontology 与阿里 UModel 架构异同",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/06-umodel-alibaba-semantic-runtime.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/06-umodel-alibaba-semantic-runtime.md",
    ),
]

# ── 4. Palantir AIP 官方文档核心产品模块（按体系拆解）──────────────────────
OFFICIAL_AIP_DOCS = [
    ("AIP 官方文档：AIP 平台总览与核心架构", "https://www.palantir.com/docs/foundry/aip/overview/"),
    ("AIP 官方文档：Agent Stack 与工具调用体系", "https://www.palantir.com/docs/foundry/aip/agent-stack/"),
    ("AIP 官方文档：AIP 核心功能模块矩阵", "https://www.palantir.com/docs/foundry/aip/aip-features/"),
    ("AIP 官方文档：用 Markings 控制 LLM 数据访问权限", "https://www.palantir.com/docs/foundry/aip/control-llm-data-access-with-markings/"),
    ("AIP 官方文档：AIP 安全架构与数据护栏", "https://www.palantir.com/docs/foundry/aip/aip-security/"),
    ("AIP 官方文档：AIP 可观测性与生产追踪 (Observability)", "https://www.palantir.com/docs/foundry/aip/aip-observability/"),
    ("AIP 官方文档：AI 伦理治理与人工审查闭环", "https://www.palantir.com/docs/foundry/aip/ethics-governance/"),
    ("AIP 官方文档：企业级 Prompt 工程最佳实践", "https://www.palantir.com/docs/foundry/aip/best-practices-prompt-engineering/"),
    ("AIP 官方文档：接入自有模型 (BYOM) 架构设计", "https://www.palantir.com/docs/foundry/aip/bring-your-own-model/"),
    ("AIP 官方文档：计算模块驱动的模型服务 (Compute Modules)", "https://www.palantir.com/docs/foundry/aip/compute-module-backed-models/"),
    ("AIP 官方文档：构建 LLM 代理与联邦层 (Proxy / Federation)", "https://www.palantir.com/docs/foundry/aip/build-a-proxy-or-federation-layer/"),
    ("AIP 官方文档：LLM 容量管理与限流机制", "https://www.palantir.com/docs/foundry/aip/llm-capacity-management/"),
]

# ── 硬过滤黑名单词（直接剔除财经股评、政治口水、招聘、周边售卖）──────────────
NOISE_KEYWORDS = [
    "nasdaq:pltr", "nyse:pltr", "rule of 40", "cathie wood", "buy the dip",
    "unjustifiable price", "never be cheap", "stock price", "share price",
    "165% retention", "motley fool", "seeking alpha", "zacks", "barron",
    "democrat", "republican", "midterm", "election", "progressive",
    "swedish forest", "early talent hiring", "recruitment session",
    "hoodies", "windbreaker", "veterans", "s&p 500", "美股", "股价", "万亿ai公司",
]


def _localname(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def _clean_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _get_child(elem, *names):
    for child in elem:
        if _localname(child.tag) in names:
            return (child.text or "").strip()
    return ""


def _get_link(elem):
    for child in elem:
        if _localname(child.tag) == "link":
            href = (child.get("href") or "").strip()
            if href:
                return href
            if child.text and child.text.strip():
                return child.text.strip()
    return ""


def is_noise(title, summary=""):
    """判断是否为纯股价财经、政治口水、招聘或周边售卖噪音。"""
    blob = f"{title} {summary}".lower()
    for kw in NOISE_KEYWORDS:
        if kw in blob:
            return True
    # 必须与 Palantir / AIP / Ontology / Foundry / Apollo 相关
    if not any(k in blob for k in ("palantir", "aip", "ontology", "foundry", "apollo", "osdk")):
        return True
    return False


def fetch_rss_source(source_name, url, limit=15):
    """抓取单个 RSS/Atom 源，提取标题、链接与正文摘要。"""
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        entries = [e for e in root.iter() if _localname(e.tag) in ("item", "entry")]
        results = []
        for e in entries[:limit]:
            title = _clean_html(_get_child(e, "title"))
            link = _get_link(e)
            # Medium / Dev.to 常在 encoded / content 中带全文
            body = _clean_html(_get_child(e, "encoded", "content", "description", "summary"))
            if not title or not link:
                continue
            if is_noise(title, body[:400]):
                continue
            results.append({
                "title": title,
                "url": link,
                "summary": body[:1500],
                "full_text": body if len(body) > 1200 else "",
                "source": source_name,
            })
        log.info(f"[{source_name}] 有效候选 {len(results)} 条")
        return results
    except Exception as e:
        log.warning(f"[{source_name}] 抓取失败: {str(e)[:100]}")
        return []


def fetch_hn_algolia():
    """通过 HackerNews Algolia API 搜索 Palantir Ontology / AIP 深度技术文章。"""
    url = "https://hn.algolia.com/api/v1/search?query=Palantir%20Ontology%20AIP&tags=story&hitsPerPage=12"
    results = []
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        resp.raise_for_status()
        for h in resp.json().get("hits", []):
            title = (h.get("title") or "").strip()
            link = (h.get("url") or "").strip()
            if not title or not link:
                continue
            if is_noise(title):
                continue
            results.append({
                "title": title,
                "url": link,
                "summary": f"HackerNews 深度讨论：{title}",
                "full_text": "",
                "source": "HackerNews 技术社区",
            })
        log.info(f"[HackerNews 技术社区] 有效候选 {len(results)} 条")
    except Exception as e:
        log.warning(f"[HackerNews] 抓取失败: {str(e)[:100]}")
    return results


def fetch_x_accounts():
    """通过 Jina Reader 抓取推特 (X) 核心账号关于 Palantir AIP / Ontology 的推文。"""
    results = []
    for source_name, handle in X_ACCOUNTS:
        url = f"https://r.jina.ai/https://x.com/{handle}"
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            if resp.status_code != 200:
                continue
            lines = [ln.strip() for ln in resp.text.split("\n") if ln.strip().startswith("*   ")]
            cnt = 0
            for ln in lines:
                # 提取推文链接（若有）
                m_url = re.search(r"https://x\.com/[A-Za-z0-9_]+/status/\d+", ln)
                tweet_url = m_url.group(0) if m_url else f"https://x.com/{handle}"
                # 清理图片和多余链接标记
                clean = re.sub(r"!\[.*?\]\(.*?\)", "", ln)
                clean = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", clean)
                clean = re.sub(r"^\*\s*(Pinned)?\s*", "", clean)
                clean = re.sub(r"\s+", " ", clean).strip()
                if len(clean) < 60:
                    continue
                # 补上 Palantir 上下文供相关性判断
                check_text = f"Palantir {clean}"
                if is_noise(check_text):
                    continue
                # 必须含产品/技术信号词才收录推文
                if not any(k in clean.lower() for k in (
                    "aip", "ontology", "foundry", "apollo", "agent", "model",
                    "workflow", "devcon", "mcp", "osdk", "enterprise", "data"
                )):
                    continue
                title = f"@{handle} 产品洞察：{clean[:70]}..."
                results.append({
                    "title": title,
                    "url": tweet_url if m_url else f"https://x.com/{handle}#{ abs(hash(clean[:40])) % 100000 }",
                    "summary": clean[:1200],
                    "full_text": clean,
                    "source": source_name,
                })
                cnt += 1
            log.info(f"[{source_name}] 有效候选 {cnt} 条")
        except Exception as e:
            log.warning(f"[{source_name}] 抓取失败: {str(e)[:100]}")
    return results


def fetch_youtube_videos():
    """搜索 YouTube 上第三方与官方关于 Palantir AIP / Ontology 的科普讲解与实操教程视频。"""
    import json as _json

    results = []
    for source_name, query, lang in YOUTUBE_SEARCH_QUERIES:
        url = f"https://www.youtube.com/results?search_query={query}"
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": UA, "Accept-Language": lang},
                timeout=20,
            )
            if resp.status_code != 200:
                continue
            m = re.search(r"var ytInitialData = (\{.*?\});</script>", resp.text)
            if not m:
                continue
            data = _json.loads(m.group(1))
            videos = []

            def _walk(obj):
                if isinstance(obj, dict):
                    if "videoRenderer" in obj:
                        vr = obj["videoRenderer"]
                        vid = vr.get("videoId", "")
                        title = "".join(
                            x.get("text", "") for x in vr.get("title", {}).get("runs", [])
                        )
                        owner = "".join(
                            x.get("text", "") for x in vr.get("ownerText", {}).get("runs", [])
                        )
                        snippets = vr.get("detailedMetadataSnippets", [{}])
                        desc = (
                            "".join(
                                x.get("text", "")
                                for x in snippets[0].get("snippetText", {}).get("runs", [])
                            )
                            if snippets
                            else ""
                        )
                        if vid and title:
                            videos.append((vid, owner, title, desc))
                    else:
                        for v in obj.values():
                            _walk(v)
                elif isinstance(obj, list):
                    for x in obj:
                        _walk(x)

            _walk(data)
            cnt = 0
            for vid, owner, title, desc in videos[:12]:
                full_title = f"[视频 · {owner}] {title}" if owner else f"[视频] {title}"
                if is_noise(full_title, desc):
                    continue
                results.append({
                    "title": full_title,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "summary": f"YouTube 频道 {owner} 视频讲解：{title}。简介：{desc}",
                    "full_text": "",
                    "source": f"{source_name} ({owner})" if owner else source_name,
                })
                cnt += 1
            log.info(f"[{source_name}] 有效视频候选 {cnt} 条")
        except Exception as e:
            log.warning(f"[{source_name}] 抓取失败: {str(e)[:100]}")
    return results


def fetch_github_study():
    """加载 GitHub 开源 Palantir AIP 深度研究专题章节。"""
    results = []
    for title, html_url, raw_url in GITHUB_STUDY_CHAPTERS:
        results.append({
            "title": title,
            "url": html_url,
            "raw_url": raw_url,
            "summary": f"开源专题《palantir-aip-study》深度拆解章节：{title}",
            "full_text": "",
            "source": "GitHub 深度专题 (palantir-aip-study)",
        })
    log.info(f"[GitHub 深度专题] 载入 {len(results)} 篇核心章节")
    return results


def fetch_official_docs():
    """加载 Palantir AIP 官方文档核心模块列表。"""
    results = []
    for title, url in OFFICIAL_AIP_DOCS:
        results.append({
            "title": title,
            "url": url,
            "summary": f"Palantir AIP 官方产品文档核心模块拆解：{title}",
            "full_text": "",
            "source": "Palantir AIP 官方文档",
        })
    log.info(f"[Palantir AIP 官方文档] 载入 {len(results)} 个功能模块")
    return results


def fetch_full_text(item, max_chars=12000):
    """
    为即将精读的 1~2 篇文章拉取完整正文：
      1. 若已有长全文（如 Medium/Dev.to RSS 内置），直接用
      2. 若有 GitHub raw_url，直接拉取 Markdown 原文
      3. 否则优先走 r.jina.ai 提取网页正文，失败则回退直接抓取 HTML 剥离标签
    """
    if item.get("full_text") and len(item["full_text"]) > 800:
        return item["full_text"][:max_chars]

    # GitHub Raw 优先
    raw_url = item.get("raw_url")
    if raw_url:
        try:
            r = requests.get(raw_url, headers={"User-Agent": UA}, timeout=20)
            if r.status_code == 200 and len(r.text) > 200:
                return r.text[:max_chars]
        except Exception as e:
            log.warning(f"GitHub Raw 拉取失败: {e}")

    url = item.get("url", "")
    if not url:
        return item.get("summary", "")

    # YouTube 视频专属提取：拉取完整视频简介/章节大纲 + 字幕轨道 (captionTracks)
    if "youtube.com/watch" in url or "youtu.be/" in url:
        try:
            import json as _json
            r = requests.get(
                url,
                headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
                timeout=20,
            )
            parts = []
            m_desc = re.search(r'"shortDescription":"((?:\\.|[^"\\])*)"', r.text)
            if m_desc:
                desc = _json.loads(f'"{m_desc.group(1)}"')
                if desc:
                    parts.append(f"【视频完整简介与章节大纲】\n{desc}")
            m_cap = re.search(r'"captionTracks":(\[\{.*?\}\])', r.text)
            if m_cap:
                tracks = _json.loads(m_cap.group(1))
                if tracks and tracks[0].get("baseUrl"):
                    rc = requests.get(tracks[0]["baseUrl"], headers={"User-Agent": UA}, timeout=15)
                    lines = re.findall(r"<text[^>]*>(.*?)</text>", rc.text)
                    transcript = _clean_html(" ".join(lines))
                    if transcript:
                        parts.append(f"【视频字幕实录】\n{transcript}")
            if parts:
                return "\n\n".join(parts)[:max_chars]
        except Exception as e:
            log.warning(f"YouTube 视频详情/字幕提取失败 ({url}): {str(e)[:80]}")

    # 1. 尝试 Jina Reader 提取干净 Markdown
    try:
        jina_url = f"https://r.jina.ai/{url}"
        r = requests.get(jina_url, headers={"User-Agent": UA}, timeout=25)
        if r.status_code == 200 and len(r.text) > 400 and "安全验证" not in r.text[:300]:
            return r.text[:max_chars]
    except Exception as e:
        log.warning(f"Jina 全文提取失败 ({url[:50]}): {str(e)[:80]}")

    # 2. 回退直接抓取网页并清理 HTML
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        if r.status_code == 200:
            html = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", r.text, flags=re.S | re.I)
            txt = _clean_html(html)
            if len(txt) > 300:
                return txt[:max_chars]
    except Exception as e:
        log.warning(f"直接抓取全文失败 ({url[:50]}): {str(e)[:80]}")

    return item.get("summary", "")


def fetch_all_candidates():
    """汇总所有深度渠道的候选内容（按 URL 去重）。"""
    all_items = []
    # 1. GitHub 深度研究章节 & 官方文档核心模块
    all_items.extend(fetch_github_study())
    all_items.extend(fetch_official_docs())
    # 2. 推特 (X) 核心账号产品动态与架构思考 + YouTube 中英文科普/实操视频
    all_items.extend(fetch_x_accounts())
    all_items.extend(fetch_youtube_videos())
    # 3. RSS 深度源（官方博客、Dev.to、Medium、精准架构搜索）
    for name, url in RSS_SOURCES:
        all_items.extend(fetch_rss_source(name, url))
    # 4. HackerNews 深度讨论
    all_items.extend(fetch_hn_algolia())

    seen = set()
    unique = []
    for it in all_items:
        u = it["url"].strip()
        if not u or u in seen:
            continue
        seen.add(u)
        unique.append(it)

    log.info(f"全渠道共汇总 {len(all_items)} 条，URL 去重后 {len(unique)} 条有效深度候选")
    return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    cands = fetch_all_candidates()
    print(f"\n共 {len(cands)} 条候选，前 15 条预览：")
    for i, c in enumerate(cands[:15], 1):
        print(f"  [{i:02d}] ({c['source']}) {c['title'][:65]}")
