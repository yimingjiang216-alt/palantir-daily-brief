#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir AIP 产品洞察 · 候选池筛选、功能点语义去重与深度解读生成模块

核心逻辑（完全围绕「帮产品团队理解 Palantir 产品功能，服务自身 AIP 规划」）：
  1. 存量+增量产品洞察池（pool.json）：
     - 不按新闻时效一刀切，只要把 Palantir 的产品功能、设计机制、工作流用法讲透的内容均入池储备。
     - 千问按「产品功能洞察价值（0~10分）」打分，并提取每篇的核心功能切面（feature_focus）。
  2. 三层去重机制：
     - 第一层（URL 永久去重）：已在 pool.json 中的链接绝不重复评估或重复发送。
     - 第二层（跨期功能点语义去重）：选今日内容时，对比已发送历史的 feature_focus 与标题，
       避免连续多天重复讲同一个已讲透的功能点。
     - 第三层（同日互补去重）：每天选 1~2 篇时，第 2 篇优先挑选不同功能切面或不同来源，保证视角互补。
  3. 产品经理友好的深度解读结构：
     - 拉取全文后由千问提炼：① 功能本质与通俗解读（善用类比/例子） ② 产品机制与功能细节拆解
       ③ 真实业务场景下的用法还原 ④ 对我们规划自研 AIP 的参考价值
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from pathlib import Path

import requests

from fetch import fetch_all_candidates, fetch_full_text

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
POOL_PATH = BASE_DIR / "pool.json"
KB_MD_PATH = BASE_DIR / "Palantir产品功能洞察库.md"

# 标准化的 Palantir 5 层产品架构坐标（用于每篇定位上下游及归档知识库章节）
ARCH_LAYERS = [
    "L1 数据接入与管道层 (Data Connection / Pipeline Builder)",
    "L2 本体与动作层 (Ontology / Object Views / Action Types / Functions)",
    "L3 Agent 编排与评测层 (AIP Logic / Agent Studio / AIP Evals)",
    "L4 交互应用与开发层 (Workshop / OSDK / Automate)",
    "L5 安全治理与工程落地 (Markings 权限 / 架构理念 / FDE 模式)",
]

# 每一层的专属产品模块强特征词（用于代码级对号入座校验，防止大模型把 L3 错分到 L1）
LAYER_RULES = [
    # (架构层索引, URL强匹配片段, 标题/功能切面强特征词)
    (
        0,  # L1 数据接入与管道层
        ("/data-connection/", "/pipeline-builder/", "/transforms/"),
        ("pipeline builder", "data connection", "数据接入", "数据清洗", "数据管道", "etl", "协议适配", "多源数据"),
    ),
    (
        2,  # L3 Agent 编排与评测层
        ("/logic/", "/agent-studio/", "/aip-evals/", "/aip/agent-stack"),
        ("aip logic", "agent studio", "aip evals", "evals", "agent stack", "model studio", "trace curation", "snapshots", "mcp", "agent 编排", "agent编排", "智能体编排", "自动化评测"),
    ),
    (
        3,  # L4 交互应用与开发层
        ("/workshop/", "/ontology-sdk/", "/automate/"),
        ("workshop", "osdk", "ontology sdk", "automate", "前端应用", "交互界面", "应用构建"),
    ),
    (
        4,  # L5 安全治理与工程落地
        ("/control-llm-data-access-with-markings", "/aip-security", "/ethics-governance", "/object-permissioning/", "02-fde-model.md", "04-action-guide"),
        ("markings", "aip-security", "permissioning", "ethics", "fde", "前线部署工程师", "驻场", "权限穿透", "安全护栏", "合规审计", "apollo", "为什么palantir", "学palantir"),
    ),
    (
        1,  # L2 本体与动作层
        ("/ontology/", "/action-types/", "/functions/", "/interfaces/", "/object-views/", "01-palantir-aip-ontology.md", "05-ontology-engineering", "06-umodel-vs-palantir"),
        ("ontology", "本体", "action types", "action type", "actions", "functions", "object type", "link type", "object views", "interface", "语义层", "动作类型", "对象绑定动作", "四原语"),
    ),
]


def resolve_arch_layer(item, llm_layer_str="", insight_title="", feature_tag=""):
    """
    锁定架构层级：
      1. 第一优先级：检查 URL 是否命中官方文档/专题的精确模块路径；
      2. 第二优先级：重点检查提炼后的洞察标题（insight_title）与模块标签（feature_tag）中的核心模块词（权重 x3），
         再结合原标题与 feature_focus（权重 x1），防止原视频标题顺带提了多个词导致误判；
      3. 第三优先级：采纳千问输出的层级并标准化为 5 个枚举值之一。
    """
    url_low = (item.get("url") or "").lower()
    primary_low = f"{insight_title} {feature_tag}".lower()
    secondary_low = f"{item.get('title', '')} {item.get('feature_focus', '')}".lower()

    # 1. URL 路径强锁定
    for idx, url_pats, _ in LAYER_RULES:
        if any(p in url_low for p in url_pats):
            return ARCH_LAYERS[idx]

    # 2. 核心标题（权重3）+ 原始标题切面（权重1）计分
    scores = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for idx, _, kw_pats in LAYER_RULES:
        for kw in kw_pats:
            if kw in primary_low:
                scores[idx] += 3
            if kw in secondary_low:
                scores[idx] += 1

    best_idx = max(scores, key=lambda k: scores[k])
    if scores[best_idx] > 0:
        return ARCH_LAYERS[best_idx]

    # 3. 兜底参考千问输出并标准化为 5 个枚举之一
    if llm_layer_str in ARCH_LAYERS:
        return llm_layer_str
    for idx, layer_name in enumerate(ARCH_LAYERS):
        if f"l{idx+1}" in (llm_layer_str or "").lower():
            return layer_name
    return ARCH_LAYERS[1]

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen-flash")
LLM_KEY = os.environ.get("LLM_API_KEY", "")

DAILY_COUNT = int(os.environ.get("DAILY_COUNT", "2"))
SCORE_CHUNK_SIZE = 15
MAX_CHUNKS_PER_RUN = 5

# ── 阶段一：产品功能洞察价值评分 Prompt ────────────────────────────────────────
SCORE_PROMPT = """你是服务于公司自研 AIP（AI Platform）产品团队的产品负责人。
目前团队正在规划公司自身的 AIP，但成员对 Palantir 的产品功能、模块设计与落地机制理解不够。

请对以下候选内容进行「Palantir 产品功能洞察价值评分（0~10分）」：

## 评分标准
- **9~10 分（极高产品参考价值）**：
  深入拆解了 Palantir AIP / Ontology / Foundry 的具体产品功能、核心概念本质、交互设计或完整业务工作流。例如：
  · 讲透某个核心产品模块是怎么设计的（如 AIP Logic、Ontology 对象与 Action 机制、Agent 工具调用、可控性旋钮、可解释性追踪、AIP Evals 评估、权限控制等）
  · 用清晰的逻辑、类比或实例把 Palantir 的产品理念和架构讲明白的深度好文
  · 详细还原客户如何用 Palantir 产品功能解决具体业务问题（订单调度、设备维护、风控等）的实战案例
- **7~8 分（优质产品功能资料）**：
  · Palantir 官方核心产品文档章节、工程博客中关于具体技术/产品特性的介绍
  · 推特(X)或技术社区上关于 Palantir 新功能发布（如 DevCon 新特性、Model Studio、MCP 集成、OSDK）的实质性功能解读
- **0~6 分（直接淘汰，不入池）**：
  · 纯财报营收、股价涨跌、估值分析（如 Rule of 40、续费率数字炒作）
  · 高管政治表态、选举相关新闻、社会抗议事件
  · 只有宏观口号或公关合作声明、没有任何具体产品功能细节的水文
  · 与 AIP/数据平台产品功能无关的纯底层运维或招聘宣传

## 候选列表
{candidates_text}

## 输出要求
严格输出 JSON 数组，提取每篇的 `score`（0~10）和 `feature_focus`（一句话概括它讲的 Palantir 具体产品功能点或概念切面，用于后续功能点去重）：
[
  {{"index": 1, "score": 9, "feature_focus": "AIP Logic 的 Agent 权限控制与自主权调节机制"}}
]
"""

# ── 阶段一（补充）：千问跨期语义去重与互补选篇 Prompt ──────────────────────────
SELECT_PROMPT = """你是服务于公司自研 AIP 产品团队的主编。
请从以下已验证有完整正文的高分候选池中，为今天挑选出最值得精读的 {count} 篇内容。

## 近期已推送过的内容（请避开相同的功能点，即使中英文表述不同也不要重复讲同一基础概念）
{recent_sent_text}

## 今日高分待选池
{candidates_text}

## 挑选原则
1. **跨期语义去重**：与近期已推送过的功能切面不重复。
2. **同日互补搭配**：选出的 {count} 篇之间视角互补（例如：1 篇偏核心架构/理念深度长文 + 1 篇偏具体功能模块实操视频/案例拆解），且来自不同渠道。
3. **直击产品功能**：优先选把 Palantir 的产品功能、Ontology 建模、AIP Logic 编排、OSDK 或客户工作流讲得最透彻的。

请严格输出选中的序号 JSON 数组（如 `[1, 3]`），不要任何额外文字：
"""

# ── 阶段二：面向产品团队的单篇全文产品洞察提炼 Prompt ──────────────────────────
DEEP_DIVE_PROMPT = """你是服务于公司自研 AIP 产品团队的首席产品专家。
产品团队正在规划公司自身的 AIP，需要每天吸收 Palantir 在产品功能设计上的精华。

请基于下面这篇资料的完整内容，为产品团队写出一份**清晰、好懂、有产品细节颗粒度的深度洞察**。

{recent_sent_context}

## 原始资料信息
- 标题：{title}
- 来源：{source}
- 核心切面：{feature_focus}
- 链接：{url}

## 原始资料正文
{full_text}

## 提炼要求
1. **聚焦 Palantir 真实的产品功能与设计逻辑（占 80% 重心）**：原汁原味把文章里涉及的 Palantir 产品功能、模块配合、数据与动作流转讲清楚，不要生搬硬套外部概念。
2. **讲人话、善用类比和具体例子**：遇到抽象概念（如 Ontology、语义层、Action、Agent 护栏、Evals 快照等），请用通俗的打比方或具象小例子帮产品经理建立直觉，不要堆砌晦涩黑话。
3. **在最后『参考价值』部分做通用启发 + 轻量框架对照与认知校准（占 20%）**：
   - 我们团队目前大体按「数据与本体认知底座（类似 Foundry/FDS） → Agent 编排与运行时（类似 AIP/Orchestrator） → 部署与运行底座（类似 Apollo/Stage） → 上层行业应用」的粗略方向在对标摸索，但早期认知还不完善。
   - 因此在写 `aip_inspiration` 时：第 1 条请聚焦 **通用 AIP 产品设计规律与认知校准**（特别是 Palantir 的真实设计与常规直觉有什么不同，帮团队刷新认知、补齐盲区）；第 2 条再轻量对照上述大方向，指出这项能力大体归属哪一层、起步阶段该怎么借鉴取舍（切忌把早期摸索概念当成死标准生套）。

请严格输出一个 JSON 对象，包含以下字段：
{{
  "title": "提炼后的中文产品洞察标题（直击该篇所讲的产品功能或设计机制，28字以内）",
  "feature_tag": "所属产品模块短标签（如：Ontology与动作建模 / AIP Logic与Agent编排 / Workshop与OSDK应用 / 权限安全与Evals评测 / 行业工作流与落地范式）",
  "arch_layer": "必须从以下5个标准架构层中精确选填1个：'L1 数据接入与管道层 (Data Connection / Pipeline Builder)' 或 'L2 本体与动作层 (Ontology / Object Views / Action Types / Functions)' 或 'L3 Agent 编排与评测层 (AIP Logic / Agent Studio / AIP Evals)' 或 'L4 交互应用与开发层 (Workshop / OSDK / Automate)' 或 'L5 安全治理与工程落地 (Markings 权限 / 架构理念 / FDE 模式)'",
  "arch_position": "架构坐标与上下游调用关系：用1~2句话讲清楚该功能在 Palantir 自身体系里处于哪一环，向上承接什么数据/对象，向下被什么模块（如 Agent、Workshop 按钮或外部业务系统）调用（70~120字）",
  "related_history": "与往期已发内容的关联：对照上方『近期已推送过的功能点』，用1句话说明本篇与之前讲过的哪个功能模块形成上下游呼应或递进补充（若无直接关联或为首期，则说明本篇在全局认知中的基础铺垫作用，50~90字）",
  "core_concept": "功能定位与通俗解读：这个功能/机制在 Palantir 里到底是什么、解决什么痛点？请结合通俗的打比方或对比（例如对比传统报表、普通RAG或传统工作流），一句话加一段简明解释帮产品经理瞬间看懂本质（120~220字）",
  "product_mechanics": [
    "功能设计细节 1（格式：『模块/机制名』：具体讲清它在产品里是怎么设计的、怎么交互或怎么流转的，带具象例子，90~150字）",
    "功能设计细节 2（同上，90~150字）",
    "功能设计细节 3（同上，若有更多关键功能点可继续列出，90~150字）"
  ],
  "scenario_usage": "在实际业务场景中怎么用：还原文中提到的具体使用场景或操作流程（例如用户/业务人员在界面上看到什么 → 触发什么 → Agent/系统后台调用什么功能模块 → 最终如何完成业务闭环，120~220字）",
  "aip_inspiration": [
    "【通用设计精髓与认知校准】提炼该机制背后的通用 AIP 产品设计规律，重点点出 Palantir 的真实做法与常规直觉有何不同、帮团队补齐什么认知盲区（75~115字）",
    "【对标框架落位与起步取舍】轻量对照『数据本体底座(FDS) / Agent编排运行时 / 部署运行底座(Stage) / 上层应用』的大体分工，说明该能力应沉淀在哪一层、当前起步阶段先借鉴什么最实用（75~115字）"
  ],
  "feature_specs": [
    {{
      "component_name": "从本篇正文中提炼出的 1 个最核心的 Palantir 具体产品功能组件/设计机制名（必须严格忠于本文核心所讲的独特组件，且不得与上方『近期已推送过的功能点』重名，格式：『英文原名/专有名（中文功能点定位）』，26字以内）",
      "arch_layer": "该功能组件所属的 L1~L5 标准架构层（从上述5个标准层中精确选1个）",
      "palantir_spec": "【Palantir 功能规格（输入/交互/规则）】只写干货产品规格：配置该功能需要定义什么输入参数或Schema？前端界面怎么交互？后台执行与校验规则是什么？（110~170字）",
      "our_action": "【我方对标落位与抄作业动作】明确对应我方哪个方向（如数据本体底座 FDS / Agent 编排运行时 / 部署底座 Stage / 上层应用），指出常规做法缺了哪一步，以及我们在写对应模块 PRD 时可直接照搬的具体功能点（100~160字）"
    }}
  ]
}}
"""

DAILY_LEAD_PROMPT = """你是服务于公司自研 AIP 产品团队的主编。
今天我们为团队挑选并拆解了以下 {count} 篇 Palantir 产品功能洞察：

{items_summary}

请写一段 **2句话（70~120字）的「今日主线导读」**：
一句话点明今天这两篇内容围绕的核心产品命题是什么；第二句话讲清这两篇之间是如何互补或递进的（例如：第1篇从架构上讲清为什么需要某机制，第2篇展示在代码/界面里怎么具体搭出来），帮产品经理带着问题意识往下读。
直接输出导读纯文本，不要标题或引号：
"""


def load_pool():
    if not POOL_PATH.exists():
        return {"updated_at": "", "items": {}}
    try:
        data = json.loads(POOL_PATH.read_text(encoding="utf-8"))
        data.setdefault("items", {})
        return data
    except Exception as e:
        log.warning(f"读取 pool.json 失败，重新初始化: {e}")
        return {"updated_at": "", "items": {}}


def save_pool(pool):
    pool["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    POOL_PATH.write_text(
        json.dumps(pool, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def call_llm(prompt, max_tokens=4000, max_retries=3):
    if not LLM_KEY:
        raise ValueError("LLM_API_KEY 未设置")

    url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {LLM_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=(30, 180))
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt < max_retries - 1:
                log.warning(f"LLM 调用失败（第 {attempt + 1} 次）: {str(e)[:80]}，8 秒后重试")
                time.sleep(8)
            else:
                raise


def _parse_json_from_llm(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        s, e = text.find(open_ch), text.rfind(close_ch)
        if s != -1 and e > s:
            try:
                return json.loads(text[s : e + 1])
            except Exception:
                continue
    return None


def _text_similarity(a, b):
    """计算两个功能点描述或标题的字符 bigram 重合度，用于跨期与同日去重。"""
    def bg(s):
        s = re.sub(r"[\s\W_]+", "", (s or "").lower())
        return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) > 1 else set()

    ba, bb = bg(a), bg(b)
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / min(len(ba), len(bb))


def update_candidate_pool(pool, candidates):
    """分批对新候选内容按「产品功能洞察价值」打分入池，并清理历史无效链接。"""
    items_map = pool.setdefault("items", {})
    invalid_doc_urls = {
        "https://www.palantir.com/docs/foundry/ontology/action-types-overview",
        "https://www.palantir.com/docs/foundry/ontology/interface-overview",
        "https://www.palantir.com/docs/foundry/logic/aip-evals",
    }
    # 清理历史遗留的 Google News 跳转空壳、假 #hash 链接及旧 404 文档地址
    stale_keys = [
        u for u in items_map
        if "news.google.com/rss/articles/" in u
        or re.search(r"#\d+$", u)
        or u in invalid_doc_urls
    ]
    for k in stale_keys:
        del items_map[k]

    # 若今日抓到的 RSS 包含完整正文（如虎嗅、Medium、Dev.to），同步补充到已在池中的条目运行时缓存
    for c in candidates:
        if c["url"] in items_map and c.get("full_text") and len(c["full_text"]) > 800:
            items_map[c["url"]]["full_text"] = c["full_text"][:10000]

    new_cands = [c for c in candidates if c["url"] not in items_map]

    if not new_cands:
        log.info("本次无新增未评估候选，直接使用池中存量")
        return

    total_to_score = new_cands[: SCORE_CHUNK_SIZE * MAX_CHUNKS_PER_RUN]
    log.info(f"发现 {len(new_cands)} 条新候选，分批评估前 {len(total_to_score)} 条...")

    added_unread = 0
    added_rejected = 0

    for start in range(0, len(total_to_score), SCORE_CHUNK_SIZE):
        batch = total_to_score[start : start + SCORE_CHUNK_SIZE]
        lines = []
        for idx, c in enumerate(batch, 1):
            lines.append(
                f"[{idx}] 来源: {c['source']}\n"
                f"标题: {c['title']}\n"
                f"摘要: {(c.get('summary') or '')[:350]}\n"
            )
        prompt = SCORE_PROMPT.format(candidates_text="\n".join(lines))
        raw = call_llm(prompt, max_tokens=2500)
        scored_list = _parse_json_from_llm(raw)

        score_by_idx = {}
        if isinstance(scored_list, list):
            for obj in scored_list:
                if isinstance(obj, dict) and "index" in obj:
                    score_by_idx[int(obj["index"])] = (
                        int(obj.get("score", 0)),
                        str(obj.get("feature_focus", "")),
                    )

        for idx, c in enumerate(batch, 1):
            default_score = 9 if "GitHub" in c["source"] else (8 if "官方文档" in c["source"] else None)
            if idx not in score_by_idx and default_score is None:
                continue

            sc, focus = score_by_idx.get(
                idx, (default_score or 0, c["title"])
            )
            if default_score and sc < default_score:
                sc = default_score

            status = "unread" if sc >= 7 else "rejected"
            if status == "unread":
                added_unread += 1
            else:
                added_rejected += 1

            items_map[c["url"]] = {
                "url": c["url"],
                "raw_url": c.get("raw_url", ""),
                "title": c["title"],
                "source": c["source"],
                "summary": c.get("summary", "")[:800],
                "full_text": (c.get("full_text") or "")[:10000],
                "score": sc,
                "feature_focus": focus or c["title"],
                "status": status,
                "added_at": datetime.now().strftime("%Y-%m-%d"),
                "sent_at": "",
            }

    save_pool(pool)
    unread_total = sum(1 for v in items_map.values() if v.get("status") == "unread")
    log.info(
        f"入池完成：新增高分待读 {added_unread} 篇，淘汰 {added_rejected} 篇；"
        f"当前池内共储备 {unread_total} 篇高分产品洞察"
    )


def select_daily_items(pool, count=2):
    """
    从池中挑选今日要发的 1~2 篇产品洞察：
      1. 按分数从高到低排，先用字面相似度做初筛
      2. 预拉取全文校验：有效正文必须 >= 400 字符（防止重定向空壳、无字幕视频或过短推文导致硬编），选出前 8 篇实料候选
      3. 调用千问（SELECT_PROMPT）对照近期已发历史做「跨期语义去重 + 同日互补搭配」，选出最终的 count 篇
    """
    items_map = pool.get("items", {})
    unread = [v for v in items_map.values() if v.get("status") == "unread"]
    if not unread:
        return []

    sent_items = [v for v in items_map.values() if v.get("status") == "sent"]
    sent_items.sort(key=lambda x: x.get("sent_at", ""), reverse=True)
    recent_sent = sent_items[:15]

    unread.sort(key=lambda x: (x.get("score", 0), x.get("added_at", "")), reverse=True)

    verified_shortlist = []
    ft_cache = {}
    pool_dirty = False

    for cand in unread:
        # 清理可能残留的临时字段
        cand.pop("_cached_full_text", None)
        cand_focus = f"{cand.get('title', '')} {cand.get('feature_focus', '')}"

        # 初筛：与近期已发内容字面高度重合的直接跳过
        if any(
            _text_similarity(cand_focus, f"{s.get('title', '')} {s.get('feature_focus', '')}") > 0.55
            for s in recent_sent
        ):
            continue

        # 校验能否抓到充足正文（>= 400 字符），避免空壳链接或过短推文
        ft = fetch_full_text(cand, max_chars=12000)
        if not ft or len(ft.strip()) < 400:
            log.info(f"跳过正文不足({len(ft or '')}字)的候选: {cand['title'][:45]}")
            cand["status"] = "insufficient_content"
            pool_dirty = True
            continue

        ft_cache[cand["url"]] = ft
        verified_shortlist.append(cand)
        if len(verified_shortlist) >= 8:
            break

    if pool_dirty:
        save_pool(pool)

    def _attach_ft(chosen_list):
        for x in chosen_list:
            if x["url"] in ft_cache:
                x["_cached_full_text"] = ft_cache[x["url"]]
        return chosen_list

    if len(verified_shortlist) <= count:
        return _attach_ft(verified_shortlist)

    # 由千问对照近期已发历史，从 8 篇实料候选中做跨语言语义去重与互补搭配
    try:
        if recent_sent:
            recent_lines = "\n".join(
                f"- [{s.get('sent_at','')}] {s.get('title','')}（切面：{s.get('feature_focus','')}）"
                for s in recent_sent
            )
        else:
            recent_lines = "（暂无历史已发记录，今天是第一期，请优先选最能帮团队建立全局架构认知 + 实操互补的 2 篇）"

        cand_lines = "\n".join(
            f"[{i}] ({c.get('score')}分 | {c.get('source')}) {c.get('title')}\n"
            f"    功能切面：{c.get('feature_focus')}"
            for i, c in enumerate(verified_shortlist, 1)
        )
        sel_raw = call_llm(
            SELECT_PROMPT.format(
                count=count,
                recent_sent_text=recent_lines,
                candidates_text=cand_lines,
            ),
            max_tokens=200,
        )
        picked_indices = _parse_json_from_llm(sel_raw)
        if isinstance(picked_indices, list):
            chosen = []
            for idx in picked_indices:
                if isinstance(idx, int) and 1 <= idx <= len(verified_shortlist):
                    c = verified_shortlist[idx - 1]
                    if c not in chosen:
                        chosen.append(c)
                if len(chosen) >= count:
                    break
            if len(chosen) == count:
                return _attach_ft(chosen)
    except Exception as e:
        log.warning(f"LLM 选篇回退规则选篇: {e}")

    # 规则兜底：优先选不同来源的前 count 篇
    fallback = [verified_shortlist[0]]
    for c in verified_shortlist[1:]:
        if c.get("source") != fallback[0].get("source"):
            fallback.append(c)
            if len(fallback) >= count:
                break
    if len(fallback) < count:
        for c in verified_shortlist[1:]:
            if c not in fallback:
                fallback.append(c)
                if len(fallback) >= count:
                    break
    return _attach_ft(fallback)


def synthesize_product_insight(item, recent_sent_focuses):
    """拉取单篇高分资料全文，生成面向产品团队的结构化产品功能洞察。"""
    focus = item.get("feature_focus") or item.get("reason") or item["title"]
    log.info(f"正在提炼产品洞察: [{item.get('score')}分] {item['title'][:50]}...")
    full_text = item.pop("_cached_full_text", None) or fetch_full_text(item, max_chars=12000)
    if not full_text or len(full_text) < 100:
        full_text = item.get("summary", item["title"])

    if recent_sent_focuses:
        recent_sent_context = (
            "## 近期已推送过的功能点（本次请侧重拆解本文独有的产品功能细节与新视角，避免重复泛泛科普）\n"
            + "\n".join(f"- {f}" for f in recent_sent_focuses[:8])
        )
    else:
        recent_sent_context = ""

    prompt = DEEP_DIVE_PROMPT.format(
        recent_sent_context=recent_sent_context,
        title=item["title"],
        source=item["source"],
        feature_focus=focus,
        url=item["url"],
        full_text=full_text,
    )
    raw = call_llm(prompt, max_tokens=3500)
    parsed = _parse_json_from_llm(raw)

    if not isinstance(parsed, dict) or not parsed.get("product_mechanics"):
        log.warning(f"产品洞察 JSON 解析兜底: {raw[:150]}")
        parsed = {
            "title": item["title"],
            "feature_tag": "AIP 产品功能洞察",
            "arch_layer": ARCH_LAYERS[1],
            "arch_position": "处于 Palantir 核心产品链路中，向上连接业务数据对象，向下支撑智能体与业务应用交互。",
            "related_history": "",
            "core_concept": item.get("summary", "")[:200],
            "product_mechanics": [item.get("summary", "")[:300]],
            "scenario_usage": "详见原文完整产品工作流说明。",
            "aip_inspiration": ["建议对照原文梳理我方 AIP 对应模块的产品功能边界。"],
        }

    # 用代码级规则 + 提炼标题 + LLM输出锁定架构层级，杜绝串层
    parsed["arch_layer"] = resolve_arch_layer(
        item,
        llm_layer_str=parsed.get("arch_layer", ""),
        insight_title=parsed.get("title", ""),
        feature_tag=parsed.get("feature_tag", ""),
    )

    # 校准每条原子级功能规格 (feature_specs) 的架构层级
    raw_specs = parsed.get("feature_specs")
    if not isinstance(raw_specs, list) or not raw_specs:
        raw_specs = [
            {
                "component_name": parsed.get("title", item["title"])[:24],
                "arch_layer": parsed["arch_layer"],
                "palantir_spec": "\n".join(parsed.get("product_mechanics", [])[:2]),
                "our_action": "\n".join(parsed.get("aip_inspiration", [])),
            }
        ]
    for sp in raw_specs:
        sp["arch_layer"] = resolve_arch_layer(
            {"url": "", "title": sp.get("component_name", ""), "feature_focus": sp.get("palantir_spec", "")[:100]},
            llm_layer_str=sp.get("arch_layer", "") or parsed["arch_layer"],
            insight_title=sp.get("component_name", ""),
            feature_tag=parsed.get("feature_tag", ""),
        )
    parsed["feature_specs"] = raw_specs

    parsed["url"] = item["url"]
    parsed["source"] = item["source"]
    parsed["score"] = item.get("score", 8)
    return parsed


def generate_daily_lead(results):
    """生成同日两篇之间的『今日主线导读』，把两篇串成有递进关系的整体。"""
    if not results:
        return ""
    if len(results) == 1:
        return f"今日聚焦【{results[0].get('feature_tag','核心模块')}】：深入拆解《{results[0].get('title','')}》的设计机制与落地用法。"
    try:
        summary_lines = []
        for idx, r in enumerate(results, 1):
            summary_lines.append(
                f"第 {idx} 篇：《{r.get('title')}》（架构层：{r.get('arch_layer')} | 来源：{r.get('source')}）\n"
                f"核心内容：{r.get('core_concept','')[:150]}"
            )
        lead = call_llm(
            DAILY_LEAD_PROMPT.format(
                count=len(results),
                items_summary="\n\n".join(summary_lines),
            ),
            max_tokens=250,
        ).strip()
        lead = re.sub(r"^[\"“「]+|[\"”」]+$", "", lead).strip()
        return lead
    except Exception as e:
        log.warning(f"生成今日导读失败: {e}")
        return (
            f"今日从『{results[0].get('feature_tag','架构原理')}』与『{results[1].get('feature_tag','实操落地')}』"
            f"两个互补视角，分别拆解《{results[0].get('title')}》与《{results[1].get('title')}》。"
        )


def generate_brief(mark_sent=False):
    """主流程：抓取候选 -> 打分入池 -> 选今日 Top 1~2 篇 -> 拉全文提炼产品功能洞察 + 今日导读。"""
    pool = load_pool()
    candidates = fetch_all_candidates()
    update_candidate_pool(pool, candidates)

    selected_raw = select_daily_items(pool, count=DAILY_COUNT)
    if not selected_raw:
        log.warning("候选池中已无未读高分文章！")
        return [], pool

    sent_items = [v for v in pool.get("items", {}).values() if v.get("status") == "sent"]
    sent_items.sort(key=lambda x: x.get("sent_at", ""), reverse=True)
    recent_focuses = [
        f"[{v.get('sent_at','')}] {v.get('title','')}（{v.get('feature_focus','')}）"
        for v in sent_items[:8]
    ]

    results = []
    for it in selected_raw:
        insight = synthesize_product_insight(it, recent_focuses)
        results.append(insight)
        recent_focuses.insert(
            0, f"[今日同批] {insight.get('title','')}（{it.get('feature_focus','')}）"
        )

    daily_lead = generate_daily_lead(results)
    for r in results:
        r["daily_lead"] = daily_lead

    if mark_sent:
        mark_items_sent(pool, [it["url"] for it in selected_raw], insights=results)

    return results, pool


def update_knowledge_base_md(pool):
    """
    根据 pool.json 中所有已发送（status=='sent'）且带有洞察归档记录的条目，
    自动生成按 Palantir 5 层产品架构分类的《Palantir产品功能洞察库.md》手册。
    """
    items_map = pool.get("items", {})
    sent_items = [v for v in items_map.values() if v.get("status") == "sent"]
    sent_items.sort(key=lambda x: (x.get("sent_at", ""), x.get("score", 0)), reverse=True)

    lines = [
        "# Palantir AIP 产品功能洞察库（按架构模块归档）",
        "",
        "> 本文档由每日推送任务自动维护更新，按 Palantir **5 层产品架构坐标**归档每一期拆解过的产品功能、核心机制与自研 AIP 启示，方便产品团队按模块查阅。",
        "",
        "## 🗺️ 全局 5 层产品架构导航",
        "",
        "```",
        "[L4 交互应用与开发层]  Workshop 操作台  |  Ontology SDK (OSDK)  |  Automate 自动触发器",
        "         ↑ 调用                     ↑ 读写                              ↑ 唤醒",
        "[L3 Agent 编排与评测]  AIP Logic (块状工具编排)  |  Agent Studio  |  AIP Evals (快照评测)",
        "         ↑ 查询对象 & 申请执行 Action",
        "[L2 本体与动作层]      Object / Property / Link (数字孪生名词)  +  Action Types / Functions (受控写回动词)",
        "         ↑ 语义映射                                                     ↓ Webhook 写回外部 ERP/SAP",
        "[L1 数据接入与管道层]  Data Connection (多模态连接器)  |  Pipeline Builder (批流一体清洗)",
        "──────────────────────────────────────────────────────────────────────────────────────────",
        "[L5 安全治理与落地范式] Markings 细粒度权限穿透  |  可解释审计追踪  |  FDE 驻场工程孵化模式",
        "```",
        "",
        f"## 📅 已推送洞察总览表（共 {len(sent_items)} 篇）",
        "",
        "| 推送日期 | 架构层级 | 洞察标题 | 核心功能切面 | 来源 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    by_layer = {layer: [] for layer in ARCH_LAYERS}

    for it in sent_items:
        arch = it.get("insight_archive") or {}
        layer = arch.get("arch_layer") or ARCH_LAYERS[1]
        if layer not in by_layer:
            layer = ARCH_LAYERS[1]
        by_layer[layer].append((it, arch))

        date_s = it.get("sent_at") or it.get("added_at") or ""
        disp_title = arch.get("title") or it.get("title", "")
        focus = it.get("feature_focus") or ""
        src = it.get("source") or "原文"
        url = it.get("url") or ""
        short_layer = layer.split(" (")[0]
        lines.append(
            f"| {date_s} | {short_layer} | **{disp_title}** | {focus} | [{src}]({url}) |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    for layer in ARCH_LAYERS:
        entries = by_layer.get(layer, [])
        lines.append(f"## {layer}（已沉淀 {len(entries)} 篇）")
        lines.append("")
        if not entries:
            lines.append("*（待后续日报解锁该层级模块拆解）*")
            lines.append("")
            continue

        for it, arch in entries:
            date_s = it.get("sent_at") or ""
            disp_title = arch.get("title") or it.get("title", "")
            url = it.get("url") or ""
            src = it.get("source") or "原文"
            lines.append(f"### 📌 [{date_s}] {disp_title}")
            lines.append(f"- **原文来源**：[{src} — {it.get('title','')}]({url})")
            if arch.get("arch_position"):
                lines.append(f"- **🗺️ 架构位置与上下游**：{arch['arch_position']}")
            if arch.get("related_history"):
                lines.append(f"- **🔗 往期关联**：{arch['related_history']}")
            if arch.get("core_concept"):
                lines.append(f"- **💡 功能本质与通俗解读**：{arch['core_concept']}")
            if arch.get("product_mechanics"):
                lines.append("- **🔧 产品功能与机制拆解**：")
                for m in arch["product_mechanics"]:
                    lines.append(f"  - {m}")
            if arch.get("scenario_usage"):
                lines.append(f"- **🔄 实际业务场景用法**：{arch['scenario_usage']}")
            if arch.get("aip_inspiration"):
                lines.append("- **🎯 对自研 AIP 的参考价值**：")
                for ins in arch["aip_inspiration"]:
                    lines.append(f"  - ★ {ins}")
            lines.append("")

    KB_MD_PATH.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"已同步更新知识库索引文档: {KB_MD_PATH.name}（共归档 {len(sent_items)} 篇）")


def mark_items_sent(pool, urls, insights=None):
    today = datetime.now().strftime("%Y-%m-%d")
    items_map = pool.get("items", {})
    insight_by_url = {x["url"]: x for x in (insights or []) if x.get("url")}

    for u in urls:
        if u in items_map:
            items_map[u]["status"] = "sent"
            items_map[u]["sent_at"] = today
            if u in insight_by_url:
                ins = insight_by_url[u]
                items_map[u]["insight_archive"] = {
                    "title": ins.get("title", ""),
                    "feature_tag": ins.get("feature_tag", ""),
                    "arch_layer": ins.get("arch_layer", ARCH_LAYERS[1]),
                    "arch_position": ins.get("arch_position", ""),
                    "related_history": ins.get("related_history", ""),
                    "core_concept": ins.get("core_concept", ""),
                    "product_mechanics": ins.get("product_mechanics", []),
                    "scenario_usage": ins.get("scenario_usage", ""),
                    "aip_inspiration": ins.get("aip_inspiration", []),
                    "feature_specs": ins.get("feature_specs", []),
                }
    save_pool(pool)
    update_knowledge_base_md(pool)
    unread_left = sum(1 for v in items_map.values() if v.get("status") == "unread")
    log.info(f"已标记 {len(urls)} 篇为 sent 并归档至知识库，池内剩余未读高分产品洞察：{unread_left} 篇")
