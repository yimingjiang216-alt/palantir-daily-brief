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
1. **聚焦产品功能与设计逻辑**：把文章里涉及的 Palantir 产品功能、模块配合、数据与动作流转讲清楚。
2. **讲人话、善用类比和具体例子**：遇到抽象概念（如 Ontology、语义层、Action、Agent 护栏等），请用通俗的打比方或具象小例子帮产品经理建立直觉，不要堆砌晦涩黑话。
3. **落脚到自研 AIP 的产品参考**：明确指出这个功能设计对我们自己规划 AIP 有什么具体启发。

请严格输出一个 JSON 对象，包含以下字段：
{{
  "title": "提炼后的中文产品洞察标题（直击该篇所讲的产品功能或设计机制，28字以内）",
  "feature_tag": "所属产品模块标签（如：Ontology与动作建模 / AIP Logic与Agent编排 / 权限安全与评估治理 / 行业工作流与落地案例 / 产品理念与架构设计）",
  "core_concept": "功能定位与通俗解读：这个功能/机制在 Palantir 里到底是什么、解决什么痛点？请结合通俗的打比方或对比（例如对比传统报表、普通RAG或传统工作流），一句话加一段简明解释帮产品经理瞬间看懂本质（120~220字）",
  "product_mechanics": [
    "功能设计细节 1（格式：『模块/机制名』：具体讲清它在产品里是怎么设计的、怎么交互或怎么流转的，带具象例子，90~150字）",
    "功能设计细节 2（同上，90~150字）",
    "功能设计细节 3（同上，若有更多关键功能点可继续列出，90~150字）"
  ],
  "scenario_usage": "在实际业务场景中怎么用：还原文中提到的具体使用场景或操作流程（例如用户/业务人员在界面上看到什么 → 触发什么 → Agent/系统后台调用什么功能模块 → 最终如何完成业务闭环，120~220字）",
  "aip_inspiration": [
    "对我们规划自研 AIP 的产品启示 1（具体到产品功能规划、交互设计或架构取舍上的可借鉴点，70~110字）",
    "对我们规划自研 AIP 的产品启示 2（同上，70~110字）"
  ]
}}
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
    # 清理历史遗留的 Google News 跳转空壳与假 #hash 链接
    stale_keys = [
        u for u in items_map
        if "news.google.com/rss/articles/" in u or re.search(r"#\d+$", u)
    ]
    for k in stale_keys:
        del items_map[k]

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
    pool_dirty = False

    for cand in unread:
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

        cand["_cached_full_text"] = ft
        verified_shortlist.append(cand)
        if len(verified_shortlist) >= 8:
            break

    if pool_dirty:
        save_pool(pool)

    if len(verified_shortlist) <= count:
        return verified_shortlist

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
                return chosen
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
    return fallback


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
            "core_concept": item.get("summary", "")[:200],
            "product_mechanics": [item.get("summary", "")[:300]],
            "scenario_usage": "详见原文完整产品工作流说明。",
            "aip_inspiration": ["建议对照原文梳理我方 AIP 对应模块的产品功能边界。"],
        }

    parsed["url"] = item["url"]
    parsed["source"] = item["source"]
    parsed["score"] = item.get("score", 8)
    return parsed


def generate_brief(mark_sent=False):
    """主流程：抓取候选 -> 打分入池 -> 选今日 Top 1~2 篇 -> 拉全文提炼产品功能洞察。"""
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
        v.get("feature_focus") or v.get("title", "") for v in sent_items[:8]
    ]

    results = []
    for it in selected_raw:
        insight = synthesize_product_insight(it, recent_focuses)
        results.append(insight)
        recent_focuses.insert(0, it.get("feature_focus") or it["title"])

    if mark_sent:
        mark_items_sent(pool, [it["url"] for it in selected_raw])

    return results, pool


def mark_items_sent(pool, urls):
    today = datetime.now().strftime("%Y-%m-%d")
    items_map = pool.get("items", {})
    for u in urls:
        if u in items_map:
            items_map[u]["status"] = "sent"
            items_map[u]["sent_at"] = today
    save_pool(pool)
    unread_left = sum(1 for v in items_map.values() if v.get("status") == "unread")
    log.info(f"已标记 {len(urls)} 篇为 sent，池内剩余未读高分产品洞察：{unread_left} 篇")
