#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir AIP 产品洞察 · 采纳组件自动转标准 PRD 初稿模块（第 2 步闭环）

闭环链路：
  ① In-the-Loop（人工）：在产品经理在飞书多维表格《01_市场与竞品洞察库》中，
     把某条功能组件的「我方采纳评估」字段标为「🔥 必抄核心机制」。
  ② On-the-Loop（自动）：本模块扫描到该打标记录后，自动调用大模型生成一份
     符合团队标准命名规范的 AIP 模块 PRD 初稿，并在 [pool.json] 中落地
     `prd_drafts` 字段，避免重复起草。
  ③ 通知：生成后向飞书群推送提醒卡片，告知对应模块负责人到表 2 审阅。

用法：
  python src/prd_drafter.py                  # 扫描 + 起草 + 推送通知
  python src/prd_drafter.py --dry-run        # 只扫描与打印，不调模型、不推送
  python src/prd_drafter.py --limit 1        # 本次最多起草 1 篇
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brief import (
    LLM_MODEL,
    call_llm,
    load_pool,
    save_pool,
    _parse_json_from_llm,
)

log = logging.getLogger("prd_drafter")

# ── 飞书多维表格配置 ──────────────────────────────────────────────────────────
APP_ID = os.environ.get("FEISHU_APP_ID", "").strip()
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "").strip()
APP_TOKEN = os.environ.get("FEISHU_BITABLE_APP_TOKEN", "HgMJwBdkliKFOEkuNOPcRN03n5e").strip()
TABLE_ID = os.environ.get("FEISHU_BITABLE_TABLE_ID", "tblwrzm93a3XYFvU").strip()

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "").strip()

# 采纳评估字段的取值（需与飞书多维表格单选选项完全一致）
# 触发起草的标记：产品经理在表里选此项即表示「近期要做」
ADOPT_MARK = "🔥近期MVP可借鉴"
# 已完成状态：不再触发起草，避免重复生成
ADOPT_DONE = "✅已纳入PRD"

# 草稿存放目录（相对仓库根目录）
DRAFT_DIR = Path(__file__).resolve().parent.parent / "prd_drafts"


# ── 飞书多维表格读取 ──────────────────────────────────────────────────────────
def get_tenant_token() -> str:
    """获取飞书 tenant_access_token。"""
    if not APP_ID or not APP_SECRET:
        raise ValueError("未配置 FEISHU_APP_ID / FEISHU_APP_SECRET，无法读取多维表格")
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=20,
    ).json()
    if resp.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败: {resp.get('msg')}")
    return resp["tenant_access_token"]


def _cell_text(value) -> str:
    """把飞书多维表格单元格值统一转成文本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(item.get("text") or item.get("name") or "")
            else:
                parts.append(str(item))
        return "".join(parts).strip()
    if isinstance(value, dict):
        return (value.get("text") or value.get("name") or "").strip()
    return str(value).strip()


def fetch_adopted_records(token: str) -> list[dict]:
    """拉取多维表格中「我方采纳评估」= 🔥近期MVP可借鉴 的全部记录（排除已纳入 PRD）。"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}"}
    records: list[dict] = []
    page_token = ""
    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(url, headers=headers, params=params, timeout=30).json()
        if resp.get("code") != 0:
            raise RuntimeError(f"读取多维表格失败: {resp.get('msg')}")
        data = resp.get("data", {})
        for item in data.get("items", []):
            fields = item.get("fields", {})
            adopt = _cell_text(fields.get("我方采纳评估"))
            # 只处理标为「近期MVP可借鉴」且尚未纳入 PRD 的记录
            if ADOPT_MARK not in adopt or ADOPT_DONE in adopt:
                continue
            records.append(
                {
                    "record_id": item.get("record_id", ""),
                    "component": _cell_text(fields.get("功能组件")),
                    "arch_layer": _cell_text(fields.get("架构层级")),
                    "spec": _cell_text(fields.get("产品设计规格")),
                    "inspiration": _cell_text(fields.get("自研对标参考")),
                    "detail": _cell_text(fields.get("规格详情")),
                    "date": _cell_text(fields.get("推送日期")),
                    "url": _cell_text(fields.get("原文链接")),
                    "adopt": adopt,
                }
            )
        if not data.get("has_more"):
            break
        page_token = data.get("page_token", "")
        if not page_token:
            break
    return records


# ── 标准命名规范 ─────────────────────────────────────────────────────────────
def _layer_code(arch_layer: str) -> str:
    """从架构层级文本中提取 L1~L5 代码。"""
    m = re.search(r"(L[1-5])", arch_layer or "")
    return m.group(1) if m else "LX"


def _slugify(text: str, max_len: int = 40) -> str:
    """把组件名转成文件名安全的短标识。"""
    # 去掉中文括号内的英文补充与特殊符号
    t = re.sub(r"[（(][^）)]*[）)]", "", text or "")
    t = re.sub(r"[\s/\\:*?\"<>|,，、。；;]+", "_", t)
    t = t.strip("_")
    return t[:max_len] or "component"


def build_prd_filename(component: str, arch_layer: str, date_str: str) -> str:
    """按团队标准命名规范生成 PRD 文件名。

    规范：[PRD-AIP-{L层级}-{YYYYMMDD}] 对标Palantir_{组件标识}_设计.md
    """
    layer = _layer_code(arch_layer)
    date_compact = (date_str or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    return f"[PRD-AIP-{layer}-{date_compact}] 对标Palantir_{_slugify(component)}_设计.md"


# ── PRD 生成 Prompt ──────────────────────────────────────────────────────────
PRD_PROMPT = """你是一位资深 AIP 产品经理。现在需要把一条来自 Palantir 的参考功能组件，**转化为一份供内部研发团队评审的 PRD 初稿**。

【参考组件信息】
- 组件名称：{component}
- 架构层级：{arch_layer}
- 产品设计规格：{spec}
- 最小实现要素：{inspiration}
- 规格详情：{detail}

【输出要求】
严格输出一个 JSON 对象，不要输出任何 JSON 之外的文字，不要臆测任何未在参考信息中出现的内部系统代号。字段如下：

{{
  "prd_title": "PRD 标题（中文，面向研发评审，格式：对标 Palantir XXX 的 YYY 功能设计）",
  "background": "业务背景与痛点（150~250 字，说明我们自研 AIP 为什么需要这个能力，结合真实产品场景）",
  "goals": ["目标 1（可度量）", "目标 2", "目标 3"],
  "non_goals": ["本轮不做 1", "本轮不做 2"],
  "user_stories": [
    {{"role": "产品经理", "story": "我希望…，以便…"}}
  ],
  "core_objects": [
    {{"name": "对象/实体名", "fields": "关键字段与类型，如 status: enum(active/disabled)", "note": "说明"}}
  ],
  "interaction_flow": [
    "步骤 1：用户在界面做什么，系统返回什么",
    "步骤 2：…",
    "步骤 3：…"
  ],
  "acceptance_criteria": [
    "Given… When… Then…（可测试的验收条件 1）",
    "Given… When… Then…（2）",
    "Given… When… Then…（3）"
  ],
  "mvp_scope": "MVP 阶段的范围边界与取舍说明（100~150 字）",
  "risks": ["风险与缓解措施 1", "风险 2"],
  "open_questions": ["待研发确认的问题 1", "问题 2"]
}}

要求：
1. 所有内容必须紧贴上述「参考组件信息」，不要泛泛而谈泛 AI 套话。
2. `interaction_flow` 要具体到界面元素与系统行为，不要只写「用户操作」「系统处理」。
3. `acceptance_criteria` 必须是可测试的 Given/When/Then 格式。
4. `user_stories` 的 `story` 字段**直接从「我希望」开始**，不要以「作为…」开头（渲染时会自动加「作为 {role}」前缀）。
5. 全部使用中文（专有名词可保留英文）。
"""


def generate_prd(record: dict) -> dict:
    """调用大模型生成 PRD 初稿结构化内容。"""
    prompt = PRD_PROMPT.format(
        component=record.get("component", ""),
        arch_layer=record.get("arch_layer", ""),
        spec=record.get("spec", "") or "（无）",
        inspiration=record.get("inspiration", "") or "（无）",
        detail=(record.get("detail", "") or "")[:3000] or "（无）",
    )
    raw = call_llm(prompt, max_tokens=6000)
    prd = _parse_json_from_llm(raw)
    if not isinstance(prd, dict):
        raise ValueError(f"模型返回的 PRD 不是合法 JSON：{str(raw)[:200]}")
    return prd


# ── Markdown 渲染 ────────────────────────────────────────────────────────────
def render_prd_markdown(record: dict, prd: dict) -> str:
    """把 PRD 结构化内容渲染成 Markdown 文档。"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = []
    lines.append(f"# {prd.get('prd_title', record.get('component', 'PRD 初稿'))}")
    lines.append("")
    lines.append("> **文档状态**：`⏳ AI 初稿 · 待产品经理审阅`（In-the-Loop 环节）")
    lines.append(f"> **架构层级**：{record.get('arch_layer', '')}")
    lines.append(f"> **参考来源**：{record.get('url', '')}")
    lines.append(f"> **生成日期**：{today}")
    lines.append(f"> **生成模型**：{LLM_MODEL}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 一、业务背景与痛点")
    lines.append("")
    lines.append(prd.get("background", "（待补充）"))
    lines.append("")

    lines.append("## 二、目标与非目标")
    lines.append("")
    lines.append("### 2.1 目标")
    lines.append("")
    for g in prd.get("goals") or []:
        lines.append(f"- {g}")
    lines.append("")
    lines.append("### 2.2 本轮非目标")
    lines.append("")
    for ng in prd.get("non_goals") or []:
        lines.append(f"- {ng}")
    lines.append("")

    lines.append("## 三、用户故事")
    lines.append("")
    for us in prd.get("user_stories") or []:
        if isinstance(us, dict):
            lines.append(f"- **作为 {us.get('role', '')}**：{us.get('story', '')}")
        else:
            lines.append(f"- {us}")
    lines.append("")

    lines.append("## 四、核心对象与数据模型")
    lines.append("")
    lines.append("| 对象 | 关键字段 | 说明 |")
    lines.append("| :--- | :--- | :--- |")
    for obj in prd.get("core_objects") or []:
        if isinstance(obj, dict):
            lines.append(
                f"| `{obj.get('name', '')}` | {obj.get('fields', '')} | {obj.get('note', '')} |"
            )
    lines.append("")

    lines.append("## 五、交互流程")
    lines.append("")
    for i, step in enumerate(prd.get("interaction_flow") or [], 1):
        lines.append(f"{i}. {step}")
    lines.append("")

    lines.append("## 六、验收标准")
    lines.append("")
    for ac in prd.get("acceptance_criteria") or []:
        lines.append(f"- [ ] {ac}")
    lines.append("")

    lines.append("## 七、MVP 范围与取舍")
    lines.append("")
    lines.append(prd.get("mvp_scope", "（待补充）"))
    lines.append("")

    lines.append("## 八、风险与应对")
    lines.append("")
    for r in prd.get("risks") or []:
        lines.append(f"- {r}")
    lines.append("")

    lines.append("## 九、待确认问题")
    lines.append("")
    for q in prd.get("open_questions") or []:
        lines.append(f"- [ ] {q}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 附录：Palantir 原始参考规格")
    lines.append("")
    lines.append(f"**产品设计规格**：{record.get('spec', '')}")
    lines.append("")
    lines.append(f"**自研对标参考**：{record.get('inspiration', '')}")
    lines.append("")
    if record.get("detail"):
        lines.append(f"**规格详情**：{record.get('detail', '')[:2000]}")
        lines.append("")

    return "\n".join(lines)


# ── 飞书通知 ─────────────────────────────────────────────────────────────────
def send_prd_notice(drafts: list[dict]) -> bool:
    """向飞书群推送 PRD 初稿生成提醒卡片。"""
    if not FEISHU_WEBHOOK:
        log.warning("未配置 FEISHU_WEBHOOK，跳过通知")
        return False
    if not drafts:
        return True

    today = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = []
    lines.append(
        f"**🔔 检测到 {len(drafts)} 个组件被标记为采纳，AI 已自动起草 PRD 初稿**"
    )
    lines.append("")
    lines.append(f"日期：{today}")
    lines.append("")
    for i, d in enumerate(drafts, 1):
        lines.append(f"**{i}. {d['component']}**")
        lines.append(f"　层级：{d['arch_layer']}")
        lines.append(f"　文件名：`{d['filename']}`")
        lines.append(f"　字数：约 {d['char_count']} 字")
        lines.append("")
    lines.append("---")
    lines.append("以上 PRD 初稿已落地到仓库 `prd_drafts/` 目录，状态为「⏳ 待产品经理审阅」。")
    lines.append("请对应模块负责人确认技术方案与 MVP 边界后，转为正式 PRD。")

    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "📝 采纳组件 → PRD 初稿已生成",
                    "content": [[{"tag": "text", "text": line}] for line in lines],
                }
            }
        },
    }
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=20).json()
        ok = resp.get("code") == 0 or resp.get("StatusCode") == 0
        if ok:
            log.info("PRD 初稿通知已推送飞书群")
        else:
            log.error("PRD 初稿通知推送失败: %s", resp)
        return ok
    except Exception as exc:  # noqa: BLE001
        log.error("PRD 初稿通知推送异常: %s", exc)
        return False


# ── 主流程 ───────────────────────────────────────────────────────────────────
def run(dry_run: bool = False, limit: int = 0) -> int:
    """扫描采纳记录并起草 PRD。返回本次新生成的草稿数量。"""
    token = get_tenant_token()
    adopted = fetch_adopted_records(token)
    log.info("多维表格中标记为「%s」的记录共 %d 条", ADOPT_MARK, len(adopted))
    if not adopted:
        return 0

    pool = load_pool()
    done = pool.setdefault("prd_drafts", {})

    pending = []
    for rec in adopted:
        key = rec["record_id"] or rec["component"]
        if key in done:
            log.info("跳过已起草记录：%s（%s）", rec["component"], done[key].get("filename", ""))
            continue
        pending.append(rec)

    if limit > 0:
        pending = pending[:limit]

    if not pending:
        log.info("没有需要新起草的采纳记录")
        return 0

    log.info("待起草 %d 条：%s", len(pending), [r["component"] for r in pending])

    if dry_run:
        for rec in pending:
            fname = build_prd_filename(rec["component"], rec["arch_layer"], rec.get("date"))
            log.info("[DRY-RUN] 将生成: %s", fname)
        return 0

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    created: list[dict] = []

    for rec in pending:
        fname = build_prd_filename(rec["component"], rec["arch_layer"], rec.get("date"))
        log.info("开始起草 PRD：%s", fname)
        try:
            prd = generate_prd(rec)
        except Exception as exc:  # noqa: BLE001
            log.error("PRD 生成失败 %s: %s", rec["component"], exc)
            continue

        md = render_prd_markdown(rec, prd)
        path = DRAFT_DIR / fname
        path.write_text(md, encoding="utf-8")

        key = rec["record_id"] or rec["component"]
        done[key] = {
            "component": rec["component"],
            "arch_layer": rec["arch_layer"],
            "filename": fname,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "url": rec.get("url", ""),
        }
        created.append(
            {
                "component": rec["component"],
                "arch_layer": rec["arch_layer"],
                "filename": fname,
                "char_count": len(md),
            }
        )
        log.info("已生成 %s（%d 字）", fname, len(md))

    save_pool(pool)
    log.info("pool.json 已更新 prd_drafts 记录")

    if created:
        send_prd_notice(created)

    return len(created)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="采纳组件自动转标准 PRD 初稿")
    parser.add_argument("--dry-run", action="store_true", help="只扫描与打印，不调模型、不推送")
    parser.add_argument("--limit", type=int, default=0, help="本次最多起草 N 篇（0 表示不限）")
    args = parser.parse_args()

    try:
        n = run(dry_run=args.dry_run, limit=args.limit)
        log.info("本次新生成 PRD 初稿 %d 篇", n)
        return 0
    except Exception as exc:  # noqa: BLE001
        log.error("执行失败: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
