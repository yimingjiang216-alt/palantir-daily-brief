#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir 动态日报 · 简报生成
把抓到的素材交给 LLM，整理成 3~6 条中文简报，每条一句话要点 + 对 AIP 团队的参考价值。
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path

import requests

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
LAST_SENT = BASE_DIR / "last_sent.json"

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen-flash")
LLM_KEY = os.environ.get("LLM_API_KEY", "")

# ── 简报口径（来自交接文档的现网 prompt）────────────────────────────────────
PROMPT_TEMPLATE = """你是一个科技行业情报分析师，服务于 AIP 产品团队。

下面是从多个信息源抓到的 Palantir 相关资讯。请整理成一份**中文行业洞察简报**，用于工作日早上的行业动态日报。

## 内容要求

1. 选出 **3~6 条**最有价值的动态。优先级从高到低：
   - 产品发布、功能更新（尤其 Foundry / AIP / Apollo 三条产品线）
   - 客户/政府合同、重大商业合作
   - 财报、股价等经营表现
   - CEO（Alex Karp）的重大公开表态
   - 技术博客、工程实践

2. **每条包含两部分**：
   - 一句话要点（说清发生了什么，简洁）
   - 对 AIP 产品团队的参考价值/影响简评（这条对我们有什么用）

3. 简报要**精简明了**，适合在群里直接阅读，不做长篇分析。

4. 如果素材里几乎没有有价值的动态，就**如实给少几条**，不要硬凑，不要拿无关内容充数。

## 素材

{materials}

## 输出格式

严格输出 JSON 数组，不要任何其他文字：

[
  {{
    "index": 1,
    "title": "一句话要点",
    "insight": "对 AIP 产品团队的参考价值",
    "url": "对应素材的原始链接",
    "source": "来源名称"
  }}
]
"""


def _load_last_sent():
    """读取已发过的标题，用于跨期去重。"""
    if not LAST_SENT.exists():
        return []
    try:
        data = json.loads(LAST_SENT.read_text(encoding="utf-8"))
        return data.get("titles", [])
    except Exception:
        return []


def _save_last_sent(titles, date_str):
    """保存本期标题，保留最近 30 条。"""
    old = _load_last_sent()
    merged = titles + [t for t in old if t not in titles]
    LAST_SENT.write_text(
        json.dumps({"date": date_str, "titles": merged[:30]},
                   ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def build_materials(items, max_chars=800):
    """把素材拼成 LLM 可读的文本。"""
    lines = []
    for i, it in enumerate(items, 1):
        pub = it["pub"].strftime("%Y-%m-%d") if it.get("pub") else "未知"
        lines.append(
            f"[{i}] 来源:{it['source']} 日期:{pub}\n"
            f"标题:{it['title']}\n"
            f"链接:{it['url']}\n"
            f"摘要:{(it.get('summary') or '')[:max_chars]}\n"
        )
    return "\n".join(lines)


def call_llm(prompt, max_retries=3):
    """调用 LLM，带重试。"""
    if not LLM_KEY:
        raise ValueError("LLM_API_KEY 未设置")

    url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "max_tokens": 4000,
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
                log.warning(f"LLM 调用失败（第{attempt+1}次）: {str(e)[:80]}，10秒后重试")
                import time
                time.sleep(10)
            else:
                raise


def parse_response(text):
    """解析 LLM 输出，容忍常见的格式问题。"""
    text = text.strip().replace("```json", "").replace("```", "").strip()

    # 正常情况：JSON 数组
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    # 兜底：LLM 输出多个独立对象（每行一个），手动包成数组
    if text.lstrip().startswith("{"):
        objs = [ln.strip().rstrip(",") for ln in text.split("\n")
                if ln.strip().startswith("{")]
        if objs:
            try:
                return json.loads("[" + ",".join(objs) + "]")
            except json.JSONDecodeError:
                pass

    log.error(f"JSON 解析失败，原始输出前 200 字：{text[:200]}")
    return []


def is_duplicate(title, prev_titles, threshold=0.6):
    """跨期去重：标题 bigram 重合率超阈值判为重复。"""
    def bigrams(s):
        s = re.sub(r"\s+", "", s).lower()
        return set(s[k:k + 2] for k in range(len(s) - 1)) if len(s) > 1 else set()

    t_bg = bigrams(title)
    if not t_bg:
        return False

    for prev in prev_titles:
        p_bg = bigrams(prev)
        if not p_bg:
            continue
        overlap = len(t_bg & p_bg) / min(len(t_bg), len(p_bg))
        if overlap > threshold:
            return True
    return False


def generate_brief(items):
    """主流程：素材 → LLM → 去重 → 简报条目列表。"""
    if not items:
        log.warning("没有素材，跳过")
        return []

    prev_titles = _load_last_sent()
    materials = build_materials(items)
    prompt = PROMPT_TEMPLATE.format(materials=materials)

    log.info(f"送 LLM 素材 {len(items)} 条，prompt {len(prompt)} 字符")
    raw = call_llm(prompt)
    log.info(f"LLM 返回 {len(raw)} 字符")

    parsed = parse_response(raw)
    if not parsed:
        log.error("LLM 输出解析失败")
        return []

    # 跨期去重
    result = []
    for it in parsed:
        title = (it.get("title") or "").strip()
        if not title:
            continue
        if is_duplicate(title, prev_titles):
            log.info(f"跨期去重: {title[:40]}")
            continue
        result.append(it)

    log.info(f"LLM 给出 {len(parsed)} 条，去重后 {len(result)} 条")
    return result


def save_brief(items, date_str):
    """保存本期标题到去重库。"""
    titles = [(it.get("title") or "").strip() for it in items if it.get("title")]
    _save_last_sent(titles, date_str)
    log.info(f"已保存 {len(titles)} 条标题到去重库")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from fetch import fetch_all

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    items = fetch_all()
    brief = generate_brief(items)
    print(f"\n{'='*60}\n共 {len(brief)} 条\n")
    for it in brief:
        print(f"【{it.get('title','')}】")
        print(f"  参考价值: {it.get('insight','')}")
        print(f"  来源: {it.get('source','')} | {it.get('url','')}\n")
