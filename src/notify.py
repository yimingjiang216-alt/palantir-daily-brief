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
import json
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
from brief import generate_brief, load_pool, mark_items_sent, save_pool

log = logging.getLogger(__name__)

FEISHU_WEBHOOK_TEST = os.environ.get("FEISHU_WEBHOOK_TEST", "").strip()
FEISHU_WEBHOOK = FEISHU_WEBHOOK_TEST or os.environ.get("FEISHU_WEBHOOK", "").strip()
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "").strip()
FEISHU_BITABLE_WEBHOOK = os.environ.get(
    "FEISHU_BITABLE_WEBHOOK",
    "https://iwpirwbutbu.feishu.cn/base/workflow/webhook/event/YqbHablSDwdxTDh7XYucP047nKd",
).strip()
FEISHU_BITABLE_URL = os.environ.get(
    "FEISHU_BITABLE_URL",
    "https://iwpirwbutbu.feishu.cn/wiki/HgMJwBdkliKFOEkuNOPcRN03n5e",
).strip()
TEST_MODE = bool(FEISHU_WEBHOOK_TEST)
FORCE_RUN = os.environ.get("FORCE_RUN", "").strip().lower() in ("1", "true", "yes")


def _gen_sign(secret, timestamp):
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def _build_feishu_post(
    items,
    date_str,
    unread_count=0,
    start_idx=1,
    include_lead=True,
    include_footer=True,
    title_suffix="",
):
    content_lines = []

    daily_lead = (items[0].get("daily_lead") or "").strip() if (items and include_lead) else ""
    if daily_lead:
        content_lines.append([
            {"tag": "text", "text": f"今日概览：{daily_lead}"}
        ])
        content_lines.append([{"tag": "text", "text": "────────────────────────"}])

    for offset, it in enumerate(items):
        idx = start_idx + offset
        title = (it.get("title") or "").strip()
        tag = (it.get("feature_tag") or "AIP 产品洞察").strip()
        arch_layer = (it.get("arch_layer") or "").split(" (")[0].strip()
        concept = (it.get("core_concept") or "").strip()
        mechanics = it.get("product_mechanics") or []
        inspirations = it.get("aip_inspiration") or []
        url = (it.get("url") or "").strip()
        source = (it.get("source") or "原文").strip()

        if offset > 0:
            content_lines.append([{"tag": "text", "text": "────────────────────────"}])

        header_badge = arch_layer if arch_layer else tag
        content_lines.append([
            {"tag": "text", "text": f"【{header_badge}】{title}"}
        ])

        if concept:
            content_lines.append([
                {"tag": "text", "text": f"1. 解决什么问题\n{concept}"}
            ])

        if mechanics:
            content_lines.append([
                {"tag": "text", "text": "2. Palantir 怎么设计的"}
            ])
            for m in mechanics[:3]:
                content_lines.append([
                    {"tag": "text", "text": f"• {m}"}
                ])

        if inspirations:
            content_lines.append([
                {"tag": "text", "text": "3. 架构取舍与最小实现要素"}
            ])
            for ins in inspirations[:2]:
                content_lines.append([
                    {"tag": "text", "text": f"• {ins}"}
                ])

        if url:
            content_lines.append([
                {"tag": "text", "text": "原文："},
                {"tag": "a", "text": f"{source}", "href": url},
            ])

    if include_footer:
        if FEISHU_BITABLE_URL:
            content_lines.append([{"tag": "text", "text": "────────────────────────"}])
            content_lines.append([
                {"tag": "text", "text": "架构知识库："},
                {
                    "tag": "a",
                    "text": "Palantir 5层产品功能洞察库（飞书多维表格）",
                    "href": FEISHU_BITABLE_URL,
                },
            ])
        elif unread_count > 0:
            content_lines.append([
                {"tag": "text", "text": f"\n候选池剩余储备：{unread_count} 篇"}
            ])

    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"Palantir AIP 产品功能洞察 · {date_str}{title_suffix}",
                    "content": content_lines,
                }
            }
        },
    }


def _post_feishu_payload(payload):
    if FEISHU_SECRET:
        ts = str(int(time.time()))
        payload["timestamp"] = ts
        payload["sign"] = _gen_sign(FEISHU_SECRET, ts)

    resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=20)
    resp.raise_for_status()
    res = resp.json()
    if res.get("code") == 0 or res.get("StatusCode") == 0:
        return True
    log.error(f"飞书返回错误: {res}")
    return False


def send_feishu(items, date_str=None, unread_count=0):
    if not items:
        log.warning("没有可推送的产品洞察内容")
        return False

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")

    if not FEISHU_WEBHOOK:
        log.info("FEISHU_WEBHOOK 当前留空，跳过飞书推送（仅在日志打印今日洞察预览）")
        if items and items[0].get("daily_lead"):
            print(f"\n今日概览：{items[0].get('daily_lead')}")
        for idx, r in enumerate(items, 1):
            arch_short = (r.get("arch_layer") or "").split(" (")[0].strip()
            print(f"\n{'=' * 66}")
            print(f"【{arch_short}】{r.get('title')}")
            print(f"1. 解决什么问题\n{r.get('core_concept')}")
            print("2. Palantir 怎么设计的")
            for m in r.get("product_mechanics", [])[:3]:
                print(f"• {m}")
            print("3. 架构取舍与最小实现要素")
            for t in r.get("aip_inspiration", [])[:2]:
                print(f"• {t}")
            print(f"原文：{r.get('source')} | {r.get('url')}")
        return False

    payload = _build_feishu_post(items, date_str, unread_count=unread_count)
    payload_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    try:
        # 单条 post 卡片不超过 24KB 时直接合并发送；若 5~6 篇内容较长超限则自动拆分为上下两篇发送
        if payload_bytes <= 24000 or len(items) <= 2:
            if _post_feishu_payload(payload):
                log.info(f"✅ 飞书推送成功，共 {len(items)} 篇产品洞察（{payload_bytes} bytes）")
                return True
            return False

        mid = (len(items) + 1) // 2
        part1 = _build_feishu_post(
            items[:mid],
            date_str,
            unread_count=unread_count,
            start_idx=1,
            include_lead=True,
            include_footer=False,
            title_suffix="（上篇）",
        )
        part2 = _build_feishu_post(
            items[mid:],
            date_str,
            unread_count=unread_count,
            start_idx=mid + 1,
            include_lead=False,
            include_footer=True,
            title_suffix="（下篇）",
        )
        ok1 = _post_feishu_payload(part1)
        time.sleep(1)
        ok2 = _post_feishu_payload(part2)
        if ok1 and ok2:
            log.info(f"✅ 飞书分片推送成功（上下两篇），共 {len(items)} 篇产品洞察")
            return True
        return ok1 or ok2
    except Exception as e:
        log.error(f"飞书推送异常: {str(e)[:150]}")
        return False


def sync_to_feishu_bitable(items, date_str=None, pool=None):
    """
    通过飞书多维表格（Bitable）自动化 Webhook，将从文章中拆解出的「Palantir 原子级产品功能组件规格 & 我方对标动作」写入多维表格。
    与群日报完全互补：群日报讲文章脉络与案例，多维表格只沉淀可直接供产品经理写 PRD 抄作业的「功能组件字典」。
    自带 URL 级永久防重锁（bitable_synced）：已入库过的文章绝不重复插入。
    """
    if not FEISHU_BITABLE_WEBHOOK or not items:
        return False

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    items_map = pool.get("items", {}) if isinstance(pool, dict) else {}
    ok_cnt = 0
    total_specs = 0

    for it in items:
        u = (it.get("url") or "").strip()
        if u and u in items_map and items_map[u].get("bitable_synced"):
            log.info(f"跳过已写入过多维表格的记录（防重复入库）: {it.get('title','')[:30]}")
            continue

        specs = it.get("feature_specs")
        if isinstance(specs, list) and len(specs) == 0:
            log.info(f"本篇无具体软件组件规格（宏观/理念类文章），跳过多维表格入库: {it.get('title','')[:30]}")
            if u and u in items_map:
                items_map[u]["bitable_synced"] = True
            continue
        if not specs:
            raw_layer = (it.get("arch_layer") or "L2 本体与动作层").strip()
            specs = [
                {
                    "component_name": (it.get("title") or "").strip(),
                    "arch_layer": raw_layer,
                    "palantir_spec": "\n".join(f"• {m}" for m in (it.get("product_mechanics") or [])),
                    "our_action": "\n".join(f"• {t}" for t in (it.get("aip_inspiration") or [])),
                }
            ]

        item_ok = True
        for sp in specs:
            total_specs += 1
            comp_name = (sp.get("component_name") or it.get("title") or "").strip()
            sp_layer = (sp.get("arch_layer") or it.get("arch_layer") or "L2 本体与动作层").split(" (")[0].strip()
            palantir_spec = (sp.get("palantir_spec") or "").strip()
            our_action = (sp.get("our_action") or "").strip()

            full_spec_card = (
                f"【产品设计规格（配置/校验/边界）】\n{palantir_spec}\n\n"
                f"【最小实现要素与代价】\n{our_action}\n\n"
                f"来源：{it.get('title','')}（{it.get('source','')}）"
            )
            row_payload = {
                "title": comp_name,
                "arch_layer": sp_layer,
                "date": date_str,
                "core_concept": palantir_spec,
                "aip_inspiration": our_action,
                "full_detail": full_spec_card,
                "url": u,
            }
            try:
                resp = requests.post(FEISHU_BITABLE_WEBHOOK, json=row_payload, timeout=15)
                resp.raise_for_status()
                ok_cnt += 1
            except Exception as e:
                item_ok = False
                log.warning(f"同步飞书多维表格功能规格失败 ({comp_name[:25]}): {str(e)[:100]}")

        if item_ok and u and u in items_map:
            items_map[u]["bitable_synced"] = True

    if ok_cnt:
        log.info(f"✅ 已实时沉淀 {ok_cnt}/{total_specs} 个原子产品功能规格至飞书多维表格")
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
        # 多维表格写入独立于群发送结果：即使群发送失败也已写入的行要落盘防重
        bitable_ok = sync_to_feishu_bitable(items, date_str=today, pool=pool)
        mark_items_sent(
            pool,
            [it["url"] for it in items],
            insights=items,
            bitable_synced=bool(bitable_ok),
        )
    elif TEST_MODE and sent_ok:
        log.info("测试群推送成功（TEST_MODE 下不消耗正式池 unread 状态、不写多维表格）")
    else:
        # 群发送失败：同步回写池状态，避免状态丢失
        try:
            save_pool(pool)
        except Exception as e:
            log.warning(f"保存池状态失败: {str(e)[:100]}")
        log.info("本次未推送飞书，文章保持 unread 状态留在池中，明日重新尝试")


if __name__ == "__main__":
    main()
