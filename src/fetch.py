#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir AIP 产品洞察 · 多渠道深度内容抓取与全文提取模块

覆盖八大类产品内容源（不设短期时效一刀切，聚焦产品功能、设计机制与业务流落地）：
  1. YouTube 三路视频源（中文第三方科普与实操 + 英文实操教程 + AIPCon 客户真机 Demo，含完整口播字幕提取）
  2. 推特 (X) 核心产品与架构账号（@PalantirTech / @chadwahl / @PalantirVision / @PalantirDev / @ssankar）
  3. 中文深度专栏与科技媒体定向源（虎嗅 Palantir 全文搜索、36氪搜索 + InfoQ/量子位/极客公园/雷峰网/钛媒体/少数派 关键词门禁）
  4. 英文深度工程与商业专栏（Dev.to #palantir、Medium #palantir / #palantir-aip / #palantir-foundry、Substack 深度长文、Towards Data Science、Stratechery、SemiAnalysis、Interconnects、MIT Tech Review、TechCrunch AI、The Decoder、HackerNews Algolia）
  5. Palantir 官方工程博客（blog.palantir.com/feed）
  6. GitHub 开源深度研究（wwwweeia/palantir-aip-study 6 篇中文万字拆解全文）
  7. Palantir 官方核心产品文档（覆盖 AIP、Ontology、AIP Logic、Agent Studio、Workshop、Automate 六大模块）
"""

import os
import re
import html
import json
import logging
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import requests

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
ANDROID_UA = "com.google.android.youtube/20.10.38 (Linux; U; Android 14)"
RSSHUB_URL = os.environ.get("RSSHUB_URL", "https://rsshub.bestblogs.dev").rstrip("/")

# ── 1. GitHub 开源深度研究（中文万字长文，支持直接拉取 Raw Markdown 全文）────
GITHUB_STUDY_CHAPTERS = [
    (
        "Palantir AIP 与 Ontology 深度拆解：数字孪生与语义操作层",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/01-palantir-aip-ontology.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/01-palantir-aip-ontology.md",
        "系统拆解 Palantir AIP 核心架构、Ontology 三层结构（语义层/动力学层/逻辑层）、OAG（Ontology Augmented Generation）与传统 RAG 的本质区别。",
    ),
    (
        "Palantir FDE（前线部署工程师）制度与产品孵化闭环",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/02-fde-model.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/02-fde-model.md",
        "深度剖析 Palantir FDE 驻场工程模式如何与 Bootcamp 配合，在客户现场快速构建 Ontology 并将定制方案沉淀为标准产品模块。",
    ),
    (
        "Palantir 企业级 AI 落地范式：从数据融合到业务流闭环",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/03-enterprise-ai-landing.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/03-enterprise-ai-landing.md",
        "完整还原制造、医疗、供应链等场景下，Palantir 如何通过数据清洗→Ontology建模→AIP Logic编排→Workshop应用→Action反向写回实现端到端落地。",
    ),
    (
        "国内企业自研 AIP 行动指南：架构借鉴与场景切入策略",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/04-action-guide-for-domestic-ai.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/04-action-guide-for-domestic-ai.md",
        "针对国内企业自研 AIP 平台，分析如何借鉴 Palantir 的语义底座、Action 闭环与人机协同旋钮，避开盲目堆砌算力与纯文本 RAG 的误区。",
    ),
    (
        "Palantir Ontology 工程设计模式：对象、关系与 Action Types 建模实践",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/05-ontology-engineering-patterns.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/05-ontology-engineering-patterns.md",
        "详解 Ontology 工程落地中的实体抽象、属性映射、多模态关联（Link Types）、动作类型（Action Types）与函数（Functions）的设计范式。",
    ),
    (
        "语义运行时对比：Palantir Ontology 与阿里 UModel 架构异同",
        "https://github.com/wwwweeia/palantir-aip-study/blob/main/06-umodel-vs-palantir-ontology.md",
        "https://raw.githubusercontent.com/wwwweeia/palantir-aip-study/main/06-umodel-vs-palantir-ontology.md",
        "对比分析 Palantir Ontology 与可观测/运维领域语义模型在实体建模、关系推理与 Agent 工具调用上的设计取舍。",
    ),
]

# ── 2. Palantir 官方核心产品文档（覆盖 AIP / Ontology / Logic / Agent Studio / Workshop / Automate）──
OFFICIAL_AIP_DOCS = [
    # AIP 核心与安全治理
    ("AIP 官方文档：产品全景与核心能力矩阵", "https://www.palantir.com/docs/foundry/aip/overview", "介绍 AIP 如何将大模型、自定义函数与业务动作锚定在企业 Ontology 之上。"),
    ("AIP 官方文档：Agent Stack 与工具调用体系", "https://www.palantir.com/docs/foundry/aip/agent-stack", "详解 AIP Agent Stack 如何封装 Ontology 查询工具、Action 执行工具与函数工具。"),
    ("AIP 官方文档：核心产品特性目录（AIP Features）", "https://www.palantir.com/docs/foundry/aip/aip-features", "梳理 AIP Logic、AIP Agent Studio、AIP Assist、AIP Evals、Workflow Builder 等模块分工。"),
    ("AIP 官方文档：通过 Markings 控制大模型数据访问权限", "https://www.palantir.com/docs/foundry/aip/control-llm-data-access-with-markings", "拆解 Palantir 如何利用细粒度安全标记（Markings）沿数据血缘穿透控制 LLM 可访问的上下文。"),
    ("AIP 官方文档：AIP 安全架构与数据护栏", "https://www.palantir.com/docs/foundry/aip/aip-security", "阐述大模型输入输出安全边界、敏感信息防泄漏、权限继承与零数据留存机制。"),
    ("AIP 官方文档：AIP 可观测性与生产环境监控", "https://www.palantir.com/docs/foundry/aip/aip-observability", "解析生产环境中如何追踪 LLM 与 Agent 的调用链路、Token 消耗与执行延迟。"),
    ("AIP 官方文档：AI 伦理治理与合规审计链路", "https://www.palantir.com/docs/foundry/aip/ethics-governance", "介绍企业高风险决策场景下的人机协同审批、可解释性溯源与合规审计设计。"),
    ("AIP 官方文档：多模型接入（BYOM）与模型路由管理", "https://www.palantir.com/docs/foundry/aip/bring-your-own-model", "说明如何接入开源或自托管大模型，并与平台内置模型统一调度。"),
    # Ontology 本体与动作层
    ("Ontology 官方文档：核心概念与数字孪生架构", "https://www.palantir.com/docs/foundry/ontology/overview", "详解 Ontology 如何把底层数据集与流数据映射为业务层的 Object、Property、Link 与 Action。"),
    ("Ontology 官方文档：Action Types（动作类型）与业务写回", "https://www.palantir.com/docs/foundry/ontology/action-types-overview", "拆解 Action Types 如何定义参数校验、权限规则、副作用与 Webhook 写回外部 ERP/业务系统。"),
    ("Ontology 官方文档：Functions on Objects（对象函数与计算模型）", "https://www.palantir.com/docs/foundry/functions/overview", "说明如何用 TypeScript/Python 编写直接读取和修改 Ontology 对象的业务规则与小模型逻辑。"),
    ("Ontology 官方文档：Interfaces（本体接口抽象与多态建模）", "https://www.palantir.com/docs/foundry/ontology/interface-overview", "详解如何用 Interface 抽象不同业务实体（如不同型号设备或不同类型工单）的共性属性与统一动作。"),
    # AIP Logic / Agent Studio / Evals / Workshop / Automate
    ("AIP Logic 官方文档：无代码编排大模型与本体工具链", "https://www.palantir.com/docs/foundry/logic/overview", "详解 AIP Logic 如何用块状思维链（Block-based CoT）组合提示词、Ontology 查询、计算函数与结构化输出。"),
    ("AIP Evals 官方文档：大模型与 Agent 自动化评测基准", "https://www.palantir.com/docs/foundry/logic/aip-evals", "拆解如何构建测试用例集、对比不同模型/Prompt 版本的准确率、耗时与成本，防止生产环境退化。"),
    ("Agent Studio 官方文档：构建与配置企业级交互式 Agent", "https://www.palantir.com/docs/foundry/agent-studio/overview", "介绍如何在 Agent Studio 中为 Agent 配置 Ontology 上下文检索、Action 工具调用权限与人工确认护栏。"),
    ("Workshop 官方文档：构建人机协同的操作应用界面", "https://www.palantir.com/docs/foundry/workshop/overview", "详解 Workshop 如何将 Ontology 对象视图、AIP Logic 推荐结果与 Action 执行按钮组装成一线业务员的操作台。"),
    ("Automate 官方文档：事件驱动的自动化监测与动作触发", "https://www.palantir.com/docs/foundry/automate/overview", "解析 Automate 如何监听 Ontology 对象状态变化或定时条件，自动唤醒 AIP Logic 并触发业务动作。"),
]

# ── 3. 推特 (X) 核心产品与架构账号（通过 r.jina.ai 渲染抓取）──────────────────
X_ACCOUNTS = [
    ("X @PalantirTech (官方产品与DevCon动态)", "PalantirTech"),
    ("X @chadwahl (Palantir Ontology架构师)", "chadwahl"),
    ("X @PalantirVision (AIP与MCP第三方拆解)", "PalantirVision"),
    ("X @ssankar (Palantir CTO产品思考)", "ssankar"),
]

# ── 4. YouTube 三路搜索（中文第三方科普/实操 + 英文实操教程 + AIPCon 真机 Demo）──
YOUTUBE_SEARCH_QUERIES = [
    ("YouTube 中文科普与架构拆解", "Palantir+本体论+OR+AIP+架构+OR+产品解析", "zh-CN,zh;q=0.9,en;q=0.8"),
    ("YouTube 英文第三方实操与架构科普", "Palantir+AIP+Ontology+tutorial+OR+explained+OR+workflow", "en-US,en;q=0.9"),
    ("YouTube AIPCon 客户真机Demo与Workshop实操", "Palantir+AIPCon+demo+OR+Workshop+AIP+Logic+walkthrough", "en-US,en;q=0.9"),
]

# ── 5. 专属聚焦 Palantir / Ontology 的 RSS 订阅源 ────────────────────────────
DEDICATED_PALANTIR_FEEDS = [
    ("虎嗅 Palantir 深度专栏", f"{RSSHUB_URL}/huxiu/search/Palantir"),
    ("Palantir 官方工程博客", "https://blog.palantir.com/feed"),
    ("Dev.to Palantir 技术专栏", "https://dev.to/feed/tag/palantir"),
    ("Medium Palantir 深度专栏", "https://medium.com/feed/tag/palantir"),
    ("Medium Palantir AIP 专栏", "https://medium.com/feed/tag/palantir-aip"),
    ("Medium Palantir Foundry 专栏", "https://medium.com/feed/tag/palantir-foundry"),
    ("Towards Data Science Ontology 专栏", "https://towardsdatascience.com/tag/ontology/feed"),
]

# ── 6. 综合深度科技媒体源（必须命中 Palantir / Ontology / 本体论 才收录）────────
BROAD_TECH_FEEDS_WITH_FILTER = [
    ("36氪-Palantir搜索", f"{RSSHUB_URL}/36kr/search/items/Palantir"),
    ("InfoQ 中文", "https://www.infoq.cn/feed"),
    ("量子位", "https://www.qbitai.com/feed"),
    ("极客公园", "https://www.geekpark.net/rss"),
    ("雷峰网", "https://www.leiphone.com/feed"),
    ("钛媒体", "https://www.tmtpost.com/rss"),
    ("少数派", "https://sspai.com/feed"),
    ("Towards Data Science", "https://towardsdatascience.com/feed"),
    ("Stratechery", "https://stratechery.com/feed/"),
    ("SemiAnalysis", "https://www.semianalysis.com/feed"),
    ("Interconnects", "https://www.interconnects.ai/feed"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Decoder", "https://the-decoder.com/feed/"),
]

# ── 7. 噪音硬过滤词（纯股价、财报炒作、政治选举、招聘宣传一律排除）──────────
NOISE_KEYWORDS = [
    "nasdaq:pltr", "nyse:pltr", "rule of 40", "cathie wood", "buy the dip",
    "unjustifiable price", "never be cheap", "stock price", "share price",
    "165% retention", "motley fool", "seeking alpha", "zacks", "barron",
    "democrat", "republican", "midterm", "election", "progressive",
    "swedish forest", "early talent hiring", "recruitment session",
    "hoodies", "windbreaker", "veterans", "s&p 500",
    "美股", "股价暴跌", "暴涨100%", "涨了4倍", "万亿ai公司", "牛市陷阱", "发战争财",
]


def _clean_html(raw):
    if not raw:
        return ""
    text = html.unescape(raw)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_noise(title, summary=""):
    blob = f"{title} {summary}".lower()
    return any(kw in blob for kw in NOISE_KEYWORDS)


def _mentions_palantir_or_ontology(title, summary=""):
    blob = f"{title} {summary}".lower()
    return any(k in blob for k in ("palantir", "ontology", "aip", "foundry", "本体论"))


def fetch_github_study():
    items = []
    for title, url, raw_url, desc in GITHUB_STUDY_CHAPTERS:
        items.append({
            "title": title,
            "url": url,
            "raw_url": raw_url,
            "summary": desc,
            "full_text": "",
            "source": "GitHub 深度专题 (palantir-aip-study)",
        })
    log.info(f"[GitHub 深度专题] 载入 {len(items)} 篇核心章节")
    return items


def fetch_official_docs():
    items = []
    for title, url, desc in OFFICIAL_AIP_DOCS:
        items.append({
            "title": title,
            "url": url,
            "summary": desc,
            "full_text": "",
            "source": "Palantir 官方产品文档",
        })
    log.info(f"[Palantir 官方产品文档] 载入 {len(items)} 个功能模块")
    return items


def fetch_x_accounts():
    """通过 r.jina.ai 抓取 X 账号推文，按独立推文列表项切分并保留真实 /status/ 链接。"""
    results = []
    for source_name, handle in X_ACCOUNTS:
        jina_url = f"https://r.jina.ai/https://x.com/{handle}"
        try:
            resp = requests.get(jina_url, headers={"User-Agent": UA}, timeout=25)
            if resp.status_code != 200 or len(resp.text) < 200:
                continue
            # Jina 渲染 X 时间线时每条推文以 "\n* " 列表项或 "Pinned " 开头
            blocks = re.split(r"\n\*\s+|\bPinned\s+", resp.text)
            cnt = 0
            for blk in blocks:
                m_status = re.search(r"https://x\.com/[A-Za-z0-9_]+/status/(\d+)", blk)
                if not m_status:
                    continue
                tweet_url = m_status.group(0)
                # 剥除图片、链接与尾部互动数字，只保留推文正文
                clean_txt = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", blk)
                clean_txt = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", clean_txt)
                clean_txt = _clean_html(clean_txt)
                clean_txt = re.sub(r"https?://\S+", "", clean_txt)
                clean_txt = re.sub(r"\s+", " ", clean_txt).strip()

                if len(clean_txt) < 120 or is_noise(clean_txt):
                    continue
                if not any(
                    k in clean_txt.lower()
                    for k in ("ontology", "aip", "agent", "eval", "foundry", "workflow", "model", "mcp", "sdk", "action", "data", "enterprise")
                ):
                    continue

                first_sentence = clean_txt[:95].rstrip(".,; ") + "..."
                results.append({
                    "title": f"@{handle} 产品洞察：{first_sentence}",
                    "url": tweet_url,
                    "summary": clean_txt[:800],
                    "full_text": "",  # 入选精读时通过 fetch_full_text 访问 tweet_url 拉取展开全文
                    "source": source_name,
                })
                cnt += 1
                if cnt >= 5:
                    break
            log.info(f"[{source_name}] 有效候选 {cnt} 条")
        except Exception as e:
            log.warning(f"[{source_name}] 抓取失败: {str(e)[:100]}")
    return results


def fetch_youtube_videos():
    """搜索 YouTube 中英文第三方科普、实操教程与 AIPCon 真机演示视频。"""
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
            data = json.loads(m.group(1))
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


def fetch_substack_articles():
    """通过 Jina 抓取 Substack 上关于 Palantir Ontology / AIP 的深度专栏长文。"""
    results = []
    search_url = "https://r.jina.ai/https://substack.com/search/Palantir%20Ontology"
    try:
        resp = requests.get(search_url, headers={"User-Agent": UA}, timeout=25)
        if resp.status_code != 200:
            return results
        # 先剥除内层嵌套的头像/配图 ![Image...](...)，防止打断外层 [文章标题+摘要](https://.../p/...) 匹配
        cleaned_md = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", resp.text)
        matches = re.findall(
            r"\[([^\]]{20,600})\]\((https://[a-zA-Z0-9._-]+/p/[a-zA-Z0-9_-]+[^)]*)\)",
            cleaned_md,
        )
        seen = set()
        for raw_text, link in matches:
            link = link.split("?")[0].rstrip("/")
            if link in seen:
                continue
            seen.add(link)
            clean_t = _clean_html(raw_text).strip()
            if len(clean_t) < 25 or is_noise(clean_t):
                continue
            title_part = clean_t[:110].strip()
            results.append({
                "title": f"[Substack] {title_part}",
                "url": link,
                "summary": clean_t[:600],
                "full_text": "",
                "source": "Substack 深度专栏",
            })
        log.info(f"[Substack 深度专栏] 有效候选 {len(results)} 条")
    except Exception as e:
        log.warning(f"[Substack 深度专栏] 抓取失败: {str(e)[:100]}")
    return results


def fetch_rss_source(source_name, url, require_palantir_kw=False):
    """通用 RSS / Atom 解析（自动保留 content:encoded 或长 description 全文）。"""
    results = []
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        atom_ns = "{http://www.w3.org/2005/Atom}"
        content_ns = "{http://purl.org/rss/1.0/modules/content/}"

        entries = root.findall(".//item")
        is_atom = False
        if not entries:
            entries = root.findall(f".//{atom_ns}entry")
            is_atom = True

        for item in entries[:20]:
            if is_atom:
                title = (item.findtext(f"{atom_ns}title") or "").strip()
                link_el = item.find(f"{atom_ns}link[@rel='alternate']") or item.find(f"{atom_ns}link")
                link = link_el.get("href", "").strip() if link_el is not None else ""
                desc = (
                    item.findtext(f"{atom_ns}content")
                    or item.findtext(f"{atom_ns}summary")
                    or ""
                )
            else:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                desc = (
                    item.findtext(f"{content_ns}encoded")
                    or item.findtext("description")
                    or ""
                )

            title = _clean_html(title)
            clean_body = _clean_html(desc)

            if not title or not link:
                continue
            if require_palantir_kw and not _mentions_palantir_or_ontology(title, clean_body):
                continue
            if is_noise(title, clean_body[:500]):
                continue

            results.append({
                "title": title,
                "url": link,
                "summary": clean_body[:800],
                "full_text": clean_body if len(clean_body) > 800 else "",
                "source": source_name,
            })
        if results or not require_palantir_kw:
            log.info(f"[{source_name}] 有效候选 {len(results)} 条")
    except Exception as e:
        if not require_palantir_kw:
            log.warning(f"[{source_name}] 抓取失败: {str(e)[:100]}")
    return results


def fetch_hn_algolia():
    """从 HackerNews Algolia 搜索关于 Palantir Ontology / AIP 的高赞深度文章。"""
    results = []
    api = "https://hn.algolia.com/api/v1/search?query=Palantir%20Ontology%20AIP&tags=story&hitsPerPage=15"
    try:
        resp = requests.get(api, headers={"User-Agent": UA}, timeout=15)
        resp.raise_for_status()
        for hit in resp.json().get("hits", []):
            title = (hit.get("title") or "").strip()
            url = (hit.get("url") or "").strip()
            points = hit.get("points") or 0
            if not title or not url or points < 3:
                continue
            if is_noise(title):
                continue
            results.append({
                "title": title,
                "url": url,
                "summary": f"HackerNews 社区技术讨论（{points} 赞，{hit.get('num_comments', 0)} 条评论）：{title}",
                "full_text": "",
                "source": "HackerNews 技术社区",
            })
        log.info(f"[HackerNews 技术社区] 有效候选 {len(results)} 条")
    except Exception as e:
        log.warning(f"[HackerNews] 抓取失败: {str(e)[:100]}")
    return results


def _fetch_youtube_full_text(url, max_chars=12000):
    """通过 YouTube InnerTube Android 接口拉取视频完整简介/章节大纲 + 完整口播字幕轨道。"""
    m_vid = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not m_vid:
        return ""
    vid = m_vid.group(1)
    parts = []
    try:
        r = requests.post(
            "https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
            json={
                "context": {
                    "client": {
                        "clientName": "ANDROID",
                        "clientVersion": "20.10.38",
                        "hl": "zh-CN",
                    }
                },
                "videoId": vid,
            },
            headers={"User-Agent": ANDROID_UA},
            timeout=20,
        )
        if r.status_code == 200:
            j = r.json()
            vd = j.get("videoDetails", {})
            desc = (vd.get("shortDescription") or "").strip()
            if desc:
                parts.append(f"【视频完整简介与章节大纲】\n{desc}")

            tracks = (
                j.get("captions", {})
                .get("playerCaptionsTracklistRenderer", {})
                .get("captionTracks", [])
            )
            if tracks:
                chosen = tracks[0]
                for tr in tracks:
                    if tr.get("languageCode", "").startswith(("zh", "en")):
                        chosen = tr
                        break
                if chosen.get("baseUrl"):
                    rc = requests.get(
                        chosen["baseUrl"],
                        headers={"User-Agent": ANDROID_UA},
                        timeout=20,
                    )
                    lines = re.findall(r"<text[^>]*>(.*?)</text>", rc.text, re.S)
                    if not lines:
                        lines = re.findall(r"<p[^>]*>(.*?)</p>", rc.text, re.S)
                    transcript = _clean_html(" ".join(lines))
                    if len(transcript) > 100:
                        parts.append(f"【视频完整口播字幕实录】\n{transcript}")
    except Exception as e:
        log.warning(f"YouTube InnerTube 提取失败 ({vid}): {str(e)[:80]}")

    return "\n\n".join(parts)[:max_chars]


def fetch_full_text(item, max_chars=12000):
    """
    为被选中准备精读的文章/视频拉取完整正文（最高 12,000 字符）：
      1. 若 RSS 已自带长全文（如虎嗅搜索、Dev.to、Medium），直接返回
      2. 若有 GitHub Raw URL，直接拉 Markdown 原文
      3. 若是 YouTube 视频，走 InnerTube 接口拉取完整章节大纲 + 完整口播字幕
      4. 其余网页优先通过 r.jina.ai 提取干净 Markdown，并剔除 Google News 空壳页
    """
    if item.get("full_text") and len(item["full_text"]) > 800:
        return item["full_text"][:max_chars]

    raw_url = item.get("raw_url")
    if raw_url:
        try:
            r = requests.get(raw_url, headers={"User-Agent": UA}, timeout=20)
            if r.status_code == 200 and len(r.text) > 300:
                return r.text[:max_chars]
        except Exception as e:
            log.warning(f"拉取 Raw Markdown 失败: {e}")

    url = item.get("url", "")
    if not url:
        return item.get("summary", "")

    # Google News 加密跳转壳无法直接提取正文，直接返回空以便上层跳过
    if "news.google.com/rss/articles/" in url:
        return ""

    # YouTube 视频专属提取
    if "youtube.com/watch" in url or "youtu.be/" in url:
        yt_text = _fetch_youtube_full_text(url, max_chars=max_chars)
        if len(yt_text) >= 350:
            return yt_text

    # 1. 尝试 Jina Reader 提取干净 Markdown
    try:
        jina_url = f"https://r.jina.ai/{url}"
        r = requests.get(jina_url, headers={"User-Agent": UA}, timeout=25)
        if r.status_code == 200 and len(r.text) > 450:
            # 过滤掉纯登录墙或跳转壳
            if "Title: Google News" not in r.text[:200]:
                return r.text[:max_chars]
    except Exception:
        pass

    # 2. 回退直接请求网页并提取文本
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        if r.status_code == 200:
            txt = _clean_html(r.text)
            if len(txt) > 450:
                return txt[:max_chars]
    except Exception:
        pass

    return item.get("summary", "")


def fetch_all_candidates():
    """汇总全部八路深度候选并按 URL 去重（同时剔除无效的跳转壳与假锚点）。"""
    all_items = []

    # 1. GitHub 开源深度研究 + Palantir 官方六大模块核心文档
    all_items.extend(fetch_github_study())
    all_items.extend(fetch_official_docs())

    # 2. 推特 (X) 核心账号 + YouTube 三路中英文科普/实操/AIPCon Demo 视频
    all_items.extend(fetch_x_accounts())
    all_items.extend(fetch_youtube_videos())

    # 3. Substack 深度长文检索
    all_items.extend(fetch_substack_articles())

    # 4. 专属聚焦 Palantir / Ontology 的 RSS 源（虎嗅全文、官方博客、Dev.to、Medium 三标签、TDS Ontology）
    for name, url in DEDICATED_PALANTIR_FEEDS:
        all_items.extend(fetch_rss_source(name, url, require_palantir_kw=False))

    # 5. 科技简报精选深度媒体源（加 Palantir / Ontology 关键词门禁过滤）
    for name, url in BROAD_TECH_FEEDS_WITH_FILTER:
        all_items.extend(fetch_rss_source(name, url, require_palantir_kw=True))

    # 6. HackerNews 技术社区
    all_items.extend(fetch_hn_algolia())

    deduped = []
    seen_urls = set()
    for it in all_items:
        u = it["url"].split("?utm_")[0].rstrip("/")
        # 剔除带 # 数字假锚点或 Google News 跳转壳的无效链接
        if re.search(r"#\d+$", u) or "news.google.com/rss/articles/" in u:
            continue
        if u in seen_urls:
            continue
        seen_urls.add(u)
        it["url"] = u
        deduped.append(it)

    log.info(f"全渠道共汇总 {len(all_items)} 条，URL 去重后 {len(deduped)} 条有效深度候选")
    return deduped
