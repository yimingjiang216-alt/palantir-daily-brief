#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir AIP 产品洞察 · 候选池打分 + 每日出队深度拆解模块
与新闻简报（report）的核心区别：
  1. 存量池模式（pool.json）：好文章不过期，所有候选先由千问按「产品机制深度」打分（0-10分）
  2. >=7 分入池排队（status="unread"），<7 分标为 rejected 永不重算
  3. 每天从池中取出分数最高的 1~2 篇未读文章，拉取全文（最高 1.2 万字），
     按《Palantir AIP 产品深度解读》样板结构生成深度产品卡片，发完标为 sent
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
SCORE_BATCH_SIZE = 45  # 每次最多对多少篇新发现文章打分

# ── 阶段一：入池筛选打分 Prompt（严格按产品设计深度打分）──────────────────────
SCORE_PROMPT = """你是服务于企业自研 AIP（AI Platform）产品团队的首席产品架构师。
请对以下候选文章/推文/文档进行「Palantir 产品机制深度评分（0~10分）」。

## 评分标准（对标《Palantir AIP 产品深度解读》）
- **9~10 分（必读级产品拆解）**：
  深入拆解 Palantir AIP / Ontology / Foundry 的核心产品机制，例如：
  · Ontology 四要素（Object / Property / Link / Action Types）与业务系统反向写回机制
  · AIP Logic 的 Agent 全生命周期设计（工具封装、自主权“旋钮”可控性、推理溯源可解释性、AIP Evals 评估、人工反馈内化、多 Agent 级联协同）
  · 端到端客户落地工作流拆解（如订单履约、设备预测性维护中人机如何基于同一套 Ontology 协同）
  · 与国内企业自研 AI 平台（如语义层、FDE 模式）的深度架构对比
- **7~8 分（优质产品/技术专题）**：
  · Palantir AIP 官方核心文档模块（Agent Stack、Markings 权限控制、Observability 追踪、Prompt 工程、BYOM）
  · 一线工程师关于 OAG（Ontology Augmented Generation）、MCP 集成、Model Studio、Trace Curation、OSDK 的技术实践或推文深度解读
- **0~6 分（直接淘汰，不入池）**：
  · 纯财报营收、股价涨跌、估值分析（如 Rule of 40、165% 续费率炒作）
  · 高管政治表态、选举站队、社会抗议新闻
  · 只有宏观口号、没有具体产品机制或工作流细节的公关通稿

## 候选列表
{candidates_text}

## 输出要求
严格输出 JSON 数组，不要任何额外解释：
[
  {{"index": 1, "score": 9, "reason": "一句话说明包含哪些产品机制点"}}
]
"""

# ── 阶段二：单篇全文深度拆解 Prompt（对标知乎样板文骨架）─────────────────────
DEEP_DIVE_PROMPT = """你是服务于公司自研 AIP 产品团队的首席产品架构师。
团队正在规划公司自身的 AIP 平台，需要深入理解 Palantir 的产品功能设计与工程落地逻辑。

请基于下面这篇资料的完整内容，写出一份**高颗粒度、拒绝空话的产品深度解读**（风格对标《Palantir AIP 产品深度解读》）。

## 原始资料信息
- 标题：{title}
- 来源：{source}
- 链接：{url}

## 原始资料正文
{full_text}

## 拆解要求（必须具体到产品原语、交互机制、数据与工作流，严禁写成公关软文）
请严格输出一个 JSON 对象，包含以下字段：
{{
  "title": "提炼后的中文深度解读标题（直击产品机制或核心架构，25字以内）",
  "module": "所属模块（从以下选一：Ontology语义与动作层 / AIP Logic与Agent生命周期 / 权限治理与安全护栏 / 企业落地工作流案例 / 平台工程与FDE模式）",
  "summary": "一句话点透这篇文章讲清楚了 Palantir 的什么核心机制（60字以内）",
  "core_mechanics": [
    "机制点1（格式：『小标题』：具体讲清原语/组件怎么设计的，比如 Object/Action 怎么绑定、权限 Markings 怎么穿透、或 Agent 自主权旋钮怎么控制，80~140字）",
    "机制点2（同上，必须有技术或产品交互细节）",
    "机制点3（同上，若有第4点也可列出）"
  ],
  "workflow_or_case": "业务场景与工作流还原：还原文中提到的具体使用场景或操作链路（例如：什么业务触发 → 接入什么数据 → Agent 调什么工具/模型 → 人工如何介入审查/反馈 → 如何通过 Action 写回业务系统；若系纯架构文档，则还原其端到端调用链路，120~220字）",
  "aip_takeaways": [
    "对我们规划自研 AIP 的启示1（必须是可以抄到产品规划里的具体设计原则，比如『人与Agent共用同一套语义原语避免认知割裂』『把自主权做成可调旋钮而非全自动黑盒』，60~100字）",
    "对我们规划自研 AIP 的启示2（同上，60~100字）"
  ]
}}
"""


def load_pool():
    """读取持久化候选池 pool.json。"""
    if not POOL_PATH.exists():
        return {"updated_at": "", "items": {}}
    try:
        return json.loads(POOL_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning(f"读取 pool.json 失败，重新初始化: {e}")
        return {"updated_at": "", "items": {}}


def save_pool(pool):
    """保存持久化候选池 pool.json。"""
    pool["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    POOL_PATH.write_text(
        json.dumps(pool, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def call_llm(prompt, max_tokens=4000, max_retries=3):
    """调用阿里云千问 OpenAI 兼容接口。"""
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
    """从 LLM 输出中提取 JSON 数组或 JSON 对象。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    # 尝试寻找最外层 [...] 或 {...}
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        s, e = text.find(open_ch), text.rfind(close_ch)
        if s != -1 and e > s:
            try:
                return json.loads(text[s : e + 1])
            except Exception:
                continue
    return None


def update_candidate_pool(pool, candidates):
    """
    把新抓到的候选文章打分入池：
      - 已在 pool["items"] 里的 URL 直接跳过（不重复消耗 Token，也不重复发送）
      - 新文章由千问按「产品机制深度」打分，>=7 分标为 unread，<7 分标为 rejected
    """
    items_map = pool.setdefault("items", {})
    new_cands = [c for c in candidates if c["url"] not in items_map]

    if not new_cands:
        log.info("本次无新增未评估候选，直接使用池中存量")
        return

    batch = new_cands[:SCORE_BATCH_SIZE]
    log.info(f"发现 {len(new_cands)} 条新候选，本次取前 {len(batch)} 条送千问打分...")

    lines = []
    for idx, c in enumerate(batch, 1):
        lines.append(
            f"[{idx}] 来源: {c['source']}\n"
            f"标题: {c['title']}\n"
            f"摘要: {(c.get('summary') or '')[:400]}\n"
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
                    str(obj.get("reason", "")),
                )

    added_unread = 0
    added_rejected = 0
    for idx, c in enumerate(batch, 1):
        # GitHub 深度研究专题与官方文档核心模块保底 8 分，防止仅凭短摘要被误杀
        default_score = 8 if ("GitHub" in c["source"] or "官方文档" in c["source"]) else 0
        sc, reason = score_by_idx.get(idx, (default_score, "默认规则评分"))
        if default_score >= 8 and sc < 8:
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
            "reason": reason,
            "status": status,
            "added_at": datetime.now().strftime("%Y-%m-%d"),
            "sent_at": "",
        }

    save_pool(pool)
    unread_total = sum(1 for v in items_map.values() if v.get("status") == "unread")
    log.info(
        f"打分入池完成：新增高分待读 {added_unread} 篇，淘汰 {added_rejected} 篇；"
        f"当前池内共储备 {unread_total} 篇高分未读文章"
    )


def synthesize_deep_dive(item):
    """拉取单篇高分文章全文，由千问生成结构化产品深度拆解。"""
    log.info(f"正在拉取全文并深度拆解: [{item['score']}分] {item['title'][:50]}...")
    full_text = fetch_full_text(item, max_chars=12000)
    if not full_text or len(full_text) < 100:
        full_text = item.get("summary", item["title"])

    prompt = DEEP_DIVE_PROMPT.format(
        title=item["title"],
        source=item["source"],
        url=item["url"],
        full_text=full_text,
    )
    raw = call_llm(prompt, max_tokens=3500)
    parsed = _parse_json_from_llm(raw)

    if not isinstance(parsed, dict) or not parsed.get("core_mechanics"):
        log.warning(f"深度拆解 JSON 解析异常，使用兜底结构: {raw[:150]}")
        parsed = {
            "title": item["title"],
            "module": "AIP 核心产品洞察",
            "summary": item.get("reason") or item.get("summary", "")[:80],
            "core_mechanics": [item.get("summary", "")[:300]],
            "workflow_or_case": "详见原文完整架构与流程拆解。",
            "aip_takeaways": ["建议结合原文对照梳理我方 AIP 的语义层与工具调用边界。"],
        }

    parsed["url"] = item["url"]
    parsed["source"] = item["source"]
    parsed["score"] = item["score"]
    return parsed


def generate_brief(mark_sent=False):
    """
    主流程：
      1. 抓取全渠道深度候选
      2. 更新持久化候选池 pool.json（对新文章打分）
      3. 从池中按分数高低取出 Top 1~2 篇 unread 文章，拉全文生成深度解读
      4. 若 mark_sent=True（或推送成功后调用 mark_items_sent），将文章标为 sent
    """
    pool = load_pool()
    candidates = fetch_all_candidates()
    update_candidate_pool(pool, candidates)

    unread = [
        v for v in pool.get("items", {}).values() if v.get("status") == "unread"
    ]
    # 排序：分数高优先；同分时优先兼顾多元来源（中文深度研究 / 社区实战 / 官方文档 / 推特）
    unread.sort(key=lambda x: (x.get("score", 0), x.get("added_at", "")), reverse=True)

    if not unread:
        log.warning("候选池中已无未读高分文章！")
        return [], pool

    # 选出今日精读的 1~2 篇（若选 2 篇，尽量让第 2 篇来自不同 source 以丰富视角）
    selected_raw = [unread[0]]
    if DAILY_COUNT > 1 and len(unread) > 1:
        second = next(
            (u for u in unread[1:] if u["source"] != selected_raw[0]["source"]),
            unread[1],
        )
        selected_raw.append(second)

    deep_dives = []
    for it in selected_raw:
        dd = synthesize_deep_dive(it)
        deep_dives.append(dd)

    if mark_sent:
        mark_items_sent(pool, [it["url"] for it in selected_raw])

    return deep_dives, pool


def mark_items_sent(pool, urls):
    """将已成功推送（或已消费）的文章在 pool.json 中标记为 sent。"""
    today = datetime.now().strftime("%Y-%m-%d")
    items_map = pool.get("items", {})
    for u in urls:
        if u in items_map:
            items_map[u]["status"] = "sent"
            items_map[u]["sent_at"] = today
    save_pool(pool)
    unread_left = sum(1 for v in items_map.values() if v.get("status") == "unread")
    log.info(f"已标记 {len(urls)} 篇为 sent，池内剩余未读高分储备：{unread_left} 篇")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    results, pool = generate_brief(mark_sent=False)
    print(f"\n{'=' * 65}\n今日生成 {len(results)} 篇 Palantir AIP 产品深度精读\n{'=' * 65}")
    for idx, r in enumerate(results, 1):
        print(f"\n【精读 {idx}】{r.get('title')}  ({r.get('module')} | 深度分 {r.get('score')})")
        print(f"▸ 核心定位：{r.get('summary')}")
        print("▸ 产品机制拆解：")
        for m in r.get("core_mechanics", []):
            print(f"   • {m}")
        print(f"▸ 业务场景与工作流还原：\n   {r.get('workflow_or_case')}")
        print("▸ 对自研 AIP 的产品启示：")
        for t in r.get("aip_takeaways", []):
            print(f"   ★ {t}")
        print(f"▸ 来源：{r.get('source')} | {r.get('url')}")
