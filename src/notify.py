#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir AIP 产品洞察 · 飞书推送模块
- 每天推送 1~2 篇聚焦「Palantir 产品功能与设计机制」的深度洞察：
  ① 功能定位与通俗解读（含类比/本质）
  ② 产品功能与机制细节拆解
  ③ 业务场景中的实际用法
  ④ 对我们规划自研 AIP 的产品启示
  ⑤ 原文链接与来源
"""

import os
import time
import base64
import hashlib
import hmac
import logging
from datetime import datetime
from pathlib import Path
import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brief import generate_brief, load_pool, mark_items_sent

log = logging.getLogger(__name__)

FEISHU_WEBHOOK_TEST = os.environ.get("FEISHU_WEBHOOK_TEST", "").strip()
FEISHU_WEBHOOK = FEISHU_WEBHOOK_TEST or os.environ.get("FEISHU_WEBHOOK", "").strip()
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "").strip()
FEISHU_BITABLE_WEBHOOK = os.environ.get("FEISHU_BITABLE_WEBHOOK", "").strip()
FEISHU_BITABLE_URL = os.environ.get("FEISHU_BITABLE_URL", "").strip()
TEST_MODE = bool(FEISHU_WEBHOOK_TEST)
FORCE_RUN = os.environ.get("FORCE_RUN", "").strip().lower() in ("1", "true", "yes")


def _gen_sign(secret, timestamp):
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def _build_feishu_post(items, date_str, unread_count=0):
    content_lines = []

    daily_lead = (items[0].get("daily_lead") or "").strip() if items else ""
    if daily_lead:
        content_lines.append([
            {"tag": "text", "text": f"📌 今日主线导读\n  {daily_lead}"}
        ])
        content_lines.append([{"tag": "text", "text": "────────────────────────"}])

    for idx, it in enumerate(items, 1):
        title = (it.get("title") or "").strip()
        tag = (it.get("feature_tag") or "AIP 产品洞察").strip()
        arch_layer = (it.get("arch_layer") or "").split(" (")[0].strip()
        arch_pos = (it.get("arch_position") or "").strip()
        related_hist = (it.get("related_history") or "").strip()
        concept = (it.get("core_concept") or "").strip()
        mechanics = it.get("product_mechanics") or []
        scenario = (it.get("scenario_usage") or "").strip()
        inspirations = it.get("aip_inspiration") or []
        url = (it.get("url") or "").strip()
        source = (it.get("source") or "原文").strip()

        if idx > 1:
            content_lines.append([{"tag": "text", "text": "────────────────────────"}])

        header_badge = f"{arch_layer} · {tag}" if arch_layer else tag
        content_lines.append([
            {"tag": "text", "text": f"【洞察 {idx} · {header_badge}】{title}"}
        ])

        if arch_pos:
            content_lines.append([
                {"tag": "text", "text": f"🗺️ 架构位置与上下游：{arch_pos}"}
            ])

        if related_hist:
            content_lines.append([
                {"tag": "text", "text": f"🔗 关联脉络：{related_hist}"}
            ])

        if concept:
            content_lines.append([
                {"tag": "text", "text": f"💡 一、功能本质与通俗解读\n  {concept}"}
            ])

        if mechanics:
            content_lines.append([
                {"tag": "text", "text": "🔧 二、产品功能与机制拆解"}
            ])
            for m in mechanics:
                content_lines.append([
                    {"tag": "text", "text": f"  • {m}"}
                ])

        if scenario:
            content_lines.append([
                {"tag": "text", "text": f"🔄 三、实际业务场景怎么用\n  {scenario}"}
            ])

        if inspirations:
            content_lines.append([
                {"tag": "text", "text": "🎯 四、对我们规划自研 AIP 的参考价值"}
            ])
            for ins in inspirations:
                content_lines.append([
                    {"tag": "text", "text": f"  ★ {ins}"}
                ])

        if url:
            content_lines.append([
                {"tag": "text", "text": "🔗 原文来源："},
                {"tag": "a", "text": f"{source}（点击查看原文）", "href": url},
            ])

    if FEISHU_BITABLE_URL:
        content_lines.append([{"tag": "text", "text": "────────────────────────"}])
        content_lines.append([
            {"tag": "text", "text": "📚 全量架构知识库："},
            {
                "tag": "a",
                "text": "👉 点击打开《Palantir 产品功能洞察库（飞书多维表格 · 按 L1~L5 架构归档）》",
                "href": FEISHU_BITABLE_URL,
            },
        ])
    elif unread_count > 0:
        content_lines.append([
            {"tag": "text", "text": f"\n📚 产品洞察池剩余高分储备：{unread_count} 篇（全部往期拆解已按 5 层架构归档至《Palantir产品功能洞察库.md》）"}
        ])

    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"Palantir AIP 产品功能洞察 · {date_str}",
                    "content": content_lines,
                }
            }
        },
    }


def send_feishu(items, date_str=None, unread_count=0):
    if not items:
        log.warning("没有可推送的产品洞察内容")
        return False

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")

    if not FEISHU_WEBHOOK:
        log.info("FEISHU_WEBHOOK 当前留空，跳过飞书推送（仅在日志打印今日洞察预览）")
        if items and items[0].get("daily_lead"):
            print(f"\n📌 今日主线导读：\n  {items[0].get('daily_lead')}")
        for idx, r in enumerate(items, 1):
            print(f"\n{'=' * 66}")
            print(f"【洞察 {idx} · {r.get('arch_layer','')} · {r.get('feature_tag')}】{r.get('title')}")
            if r.get("arch_position"):
                print(f"🗺️ 架构位置与上下游：{r.get('arch_position')}")
            if r.get("related_history"):
                print(f"🔗 关联脉络：{r.get('related_history')}")
            print(f"💡 一、功能本质与通俗解读：\n  {r.get('core_concept')}")
            print("🔧 二、产品功能与机制拆解：")
            for m in r.get("product_mechanics", []):
                print(f"  • {m}")
            print(f"🔄 三、实际业务场景怎么用：\n  {r.get('scenario_usage')}")
            print("🎯 四、对我们规划自研 AIP 的参考价值：")
            for t in r.get("aip_inspiration", []):
                print(f"  ★ {t}")
            print(f"🔗 来源：{r.get('source')} | {r.get('url')}")
        return False

    payload = _build_feishu_post(items, date_str, unread_count=unread_count)
    if FEISHU_SECRET:
        ts = str(int(time.time()))
        payload["timestamp"] = ts
        payload["sign"] = _gen_sign(FEISHU_SECRET, ts)

    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=20)
        resp.raise_for_status()
        res = resp.json()
        if res.get("code") == 0 or res.get("StatusCode") == 0:
            log.info(f"✅ 飞书推送成功，共 {len(items)} 篇产品洞察")
            return True
        log.error(f"飞书返回错误: {res}")
        return False
    except Exception as e:
        log.error(f"飞书推送异常: {str(e)[:150]}")
        return False


def sync_to_feishu_bitable(items, date_str=None):
    """
    通过飞书多维表格（Bitable）自动化 Webhook，将当日每篇洞察实时写入多维表格新增记录。
    每篇发送一次 JSON 请求，方便多维表格自动化直接映射为单行结构化字段。
    """
    if not FEISHU_BITABLE_WEBHOOK or not items:
        return False

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    ok_cnt = 0
    for it in items:
        row_payload = {
            "date": date_str,
            "arch_layer": (it.get("arch_layer") or "").strip(),
            "feature_tag": (it.get("feature_tag") or "").strip(),
            "title": (it.get("title") or "").strip(),
            "arch_position": (it.get("arch_position") or "").strip(),
            "related_history": (it.get("related_history") or "").strip(),
            "core_concept": (it.get("core_concept") or "").strip(),
            "product_mechanics": "\n".join(f"• {m}" for m in (it.get("product_mechanics") or [])),
            "scenario_usage": (it.get("scenario_usage") or "").strip(),
            "aip_inspiration": "\n".join(f"★ {t}" for t in (it.get("aip_inspiration") or [])),
            "source": (it.get("source") or "").strip(),
            "url": (it.get("url") or "").strip(),
        }
        try:
            resp = requests.post(FEISHU_BITABLE_WEBHOOK, json=row_payload, timeout=15)
            resp.raise_for_status()
            ok_cnt += 1
        except Exception as e:
            log.warning(f"同步飞书多维表格失败 ({it.get('title','')[:25]}): {str(e)[:100]}")

    if ok_cnt:
        log.info(f"✅ 已实时同步 {ok_cnt}/{len(items)} 条记录至飞书多维表格")
    return ok_cnt > 0


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    today = datetime.now().strftime("%Y-%m-%d")
    pool_pre = load_pool()
    already_sent_today = [
        v for v in pool_pre.get("items", {}).values()
        if v.get("status") == "sent" and v.get("sent_at") == today
    ]
    if already_sent_today and not TEST_MODE and not FORCE_RUN:
        log.info(
            f"今日 ({today}) 已成功推送过 {len(already_sent_today)} 篇产品洞察，"
            "跳过本次重复触发（防止外部 cron 与 GitHub schedule 双重触发连发两期）"
        )
        return

    items, pool = generate_brief(mark_sent=False)
    if not items:
        log.warning("未生成任何产品洞察内容")
        return

    unread_total = sum(
        1 for v in pool.get("items", {}).values() if v.get("status") == "unread"
    )
    unread_after = max(0, unread_total - len(items))

    sent_ok = send_feishu(items, date_str=today, unread_count=unread_after)
    if sent_ok and not TEST_MODE:
        sync_to_feishu_bitable(items, date_str=today)
        mark_items_sent(pool, [it["url"] for it in items], insights=items)
    elif sent_ok and TEST_MODE:
        log.info("测试群推送成功（TEST_MODE 下不消耗正式池 unread 状态）")
    else:
        log.info("本次未推送飞书，文章保持 unread 状态留在池中，待配置 FEISHU_WEBHOOK 后发送")


if __name__ == "__main__":
    main()
