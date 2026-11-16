#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir AIP 产品洞察 · 飞书推送模块
- 每天推送 1~2 篇结构化产品深度拆解（机制拆解 + 业务流还原 + 自研 AIP 启示 + 原文链接）
- 若 FEISHU_WEBHOOK 留空：打印完整日报预览并正常退出（仅更新候选池 pool.json，不消耗未读状态，待配好 webhook 后正式出队发送）
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
from brief import generate_brief, mark_items_sent

log = logging.getLogger(__name__)

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "").strip()
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "").strip()


def _gen_sign(secret, timestamp):
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def _build_feishu_post(items, date_str, unread_count=0):
    """构建飞书富文本（post）消息，完整呈现深度拆解的四个层次。"""
    content_lines = []

    for idx, it in enumerate(items, 1):
        title = (it.get("title") or "").strip()
        module = (it.get("module") or "AIP 产品洞察").strip()
        summary = (it.get("summary") or "").strip()
        mechanics = it.get("core_mechanics") or []
        workflow = (it.get("workflow_or_case") or "").strip()
        takeaways = it.get("aip_takeaways") or []
        url = (it.get("url") or "").strip()
        source = (it.get("source") or "原文").strip()

        if idx > 1:
            content_lines.append([{"tag": "text", "text": "────────────────────────"}])

        # 标题与模块标签
        content_lines.append([
            {"tag": "text", "text": f"【精读 {idx} · {module}】{title}"}
        ])
        if summary:
            content_lines.append([
                {"tag": "text", "text": f"💡 一句话定位：{summary}"}
            ])

        # 一、核心产品机制拆解
        if mechanics:
            content_lines.append([
                {"tag": "text", "text": "🔧 一、核心产品机制拆解"}
            ])
            for m in mechanics:
                content_lines.append([
                    {"tag": "text", "text": f"  • {m}"}
                ])

        # 二、业务场景与工作流还原
        if workflow:
            content_lines.append([
                {"tag": "text", "text": "🔄 二、业务场景与工作流还原"}
            ])
            content_lines.append([
                {"tag": "text", "text": f"  {workflow}"}
            ])

        # 三、对我们规划自研 AIP 的启示
        if takeaways:
            content_lines.append([
                {"tag": "text", "text": "🎯 三、对我们规划自研 AIP 的产品启示"}
            ])
            for t in takeaways:
                content_lines.append([
                    {"tag": "text", "text": f"  ★ {t}"}
                ])

        # 四、原文链接
        if url:
            content_lines.append([
                {"tag": "text", "text": "🔗 原文来源："},
                {"tag": "a", "text": f"{source}（点击查看原文）", "href": url},
            ])

    if unread_count > 0:
        content_lines.append([
            {"tag": "text", "text": f"\n📚 深度知识池当前剩余高分待读储备：{unread_count} 篇"}
        ])

    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"Palantir AIP 产品深度洞察 · {date_str}",
                    "content": content_lines,
                }
            }
        },
    }


def send_feishu(items, date_str=None, unread_count=0):
    """推送到飞书群机器人。若 FEISHU_WEBHOOK 为空则仅打印预览并返回 False。"""
    if not items:
        log.warning("没有可推送的深度洞察内容")
        return False

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")

    if not FEISHU_WEBHOOK:
        log.info("FEISHU_WEBHOOK 当前留空，跳过飞书推送（仅在日志打印今日精读预览）")
        for idx, r in enumerate(items, 1):
            print(f"\n【精读 {idx} · {r.get('module')}】{r.get('title')}")
            print(f"💡 定位：{r.get('summary')}")
            for m in r.get("core_mechanics", []):
                print(f"  • {m}")
            print(f"🔄 场景还原：{r.get('workflow_or_case')}")
            for t in r.get("aip_takeaways", []):
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
            log.info(f"✅ 飞书推送成功，共 {len(items)} 篇深度精读")
            return True
        log.error(f"飞书返回错误: {res}")
        return False
    except Exception as e:
        log.error(f"飞书推送异常: {str(e)[:150]}")
        return False


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    items, pool = generate_brief(mark_sent=False)
    if not items:
        log.warning("未生成任何精读内容")
        return

    unread_total = sum(
        1 for v in pool.get("items", {}).values() if v.get("status") == "unread"
    )
    unread_after = max(0, unread_total - len(items))

    sent_ok = send_feishu(items, unread_count=unread_after)
    if sent_ok:
        # 只有真正推送到飞书群成功，才将这 1~2 篇标记为 sent
        mark_items_sent(pool, [it["url"] for it in items])
    else:
        log.info("本次未推送飞书，文章保持 unread 状态留在池中，待配置 FEISHU_WEBHOOK 后发送")


if __name__ == "__main__":
    main()
