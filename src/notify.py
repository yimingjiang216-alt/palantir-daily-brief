#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Palantir 动态日报 · 飞书推送
只推飞书，不发邮件、不出 PDF。

支持两种 webhook：
  - 群自定义机器人 webhook（FEISHU_WEBHOOK）
  - 可选签名校验（FEISHU_SECRET）
"""

import os
import time
import base64
import hashlib
import hmac
import logging
from datetime import datetime

import requests

log = logging.getLogger(__name__)

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")


def _gen_sign(secret, timestamp):
    """飞书自定义机器人签名校验。"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"),
                         digestmod=hashlib.sha256).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def _build_card(items, date_str):
    """
    构建飞书消息卡片。
    用 post（富文本）而不是 card：post 对长文本自动换行，不会截断标题。
    """
    content_lines = []

    # 首行：标题
    content_lines.append([
        {"tag": "text", "text": f"【Palantir 动态日报】{date_str}"}
    ])

    # 每条：要点 + 参考价值 + 来源链接
    for i, it in enumerate(items, 1):
        title = (it.get("title") or "").strip()
        insight = (it.get("insight") or "").strip()
        url = (it.get("url") or "").strip()
        source = (it.get("source") or "").strip()

        # 序号 + 要点
        content_lines.append([{"tag": "text", "text": f"{i}. {title}"}])

        # 参考价值
        if insight:
            content_lines.append([{"tag": "text", "text": f"   参考价值：{insight}"}])

        # 来源链接
        if url:
            label = f"   → {source}" if source else "   → 原文"
            content_lines.append([
                {"tag": "a", "text": label, "href": url}
            ])

    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"Palantir 动态日报 {date_str}",
                    "content": content_lines,
                }
            }
        },
    }


def send_feishu(items, date_str=None):
    """推送到飞书。返回 True/False。"""
    if not items:
        log.warning("没有内容，跳过飞书推送")
        return False

    if not FEISHU_WEBHOOK:
        log.error("FEISHU_WEBHOOK 未设置")
        return False

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    payload = _build_card(items, date_str)

    # 签名校验
    if FEISHU_SECRET:
        ts = str(int(time.time()))
        payload["timestamp"] = ts
        payload["sign"] = _gen_sign(FEISHU_SECRET, ts)

    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=20)
        resp.raise_for_status()
        result = resp.json()

        # 飞书返回 code=0 才算成功
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            log.info(f"飞书推送成功，共 {len(items)} 条")
            return True
        else:
            log.error(f"飞书返回错误: {result}")
            return False

    except Exception as e:
        log.error(f"飞书推送失败: {str(e)[:150]}")
        return False


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from fetch import fetch_all
    from brief import generate_brief

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    items = fetch_all()
    brief = generate_brief(items)
    if brief:
        send_feishu(brief)
    else:
        log.warning("没有生成条目，不推送")
