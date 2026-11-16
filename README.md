# Palantir AIP 产品洞察日报（palantir-daily-brief）

面向公司自研 AIP 产品团队的每日 Palantir 产品功能深度拆解系统。
围绕「**把 Palantir 的产品功能、模块机制与业务场景用法讲透**」，每天自动抓取中英文图文与视频资源，经阿里云百炼千问（`qwen-flash`）评分入池、跨期语义去重、全文四层深度提炼后，**同步推送飞书群日报并静默归档至飞书多维表格知识库**。

---

## 一、整体工作流与核心逻辑（7 步闭环）

```
【Step 1 · 每日外部定时触发 (09:00 北京时间)】
  由外部调度器调用 GitHub API (workflow_dispatch) 触发云端运行。
  先读取 pool.json 检查同日防重锁（若今日 sent_at 已存在则自动跳过，防止重复发送）。
        ↓
【Step 2 · 八路内容源抓取 + 按工作日模块轮换 + 噪音硬过滤 (src/fetch.py)】
  ├─ YouTube 视频（基础中英文科普 + 周一至周五按 5 大模块轮换深挖实操/AIPCon Demo）
  ├─ 推特 (X) 4 大核心号：@PalantirTech / @chadwahl / @PalantirVision / @ssankar（真实 /status/ 链接）
  ├─ 中文深度专栏：虎嗅 Palantir 搜索（自带万字全文）、36氪 + InfoQ/量子位/极客公园/雷峰网/钛媒体/少数派
  ├─ 英文深度专栏：Medium 三标签、Dev.to、Substack（轮换搜索词）、TDS、Stratechery、SemiAnalysis、MIT Tech Review、HN
  └─ 官方与开源底座：Palantir 官方工程博客 + 官方 21 个核心文档模块 + GitHub 6 篇中文万字研究
  * 经 is_noise() 硬过滤：直接剔除股价、财报估值、政治选举、周边/招聘等非产品噪音。
        ↓
【Step 3 · 千问产品功能价值打分入池 + URL 永久去重 (src/brief.py -> pool.json)】
  已在 pool.json 中的 URL 自动跳过；仅对新发现的候选分批（15条/批）由千问按「产品功能洞察价值（0~10分）」打分，
  并提取一句话功能切面（feature_focus）：
  · >= 7 分：标记为 status="unread" 存入池中排队（若 RSS 自带长全文则同步持久化保存）
  · <  7 分：标记为 status="rejected" 永久淘汰，后续不再重复评估
        ↓
【Step 4 · 正文实料校验 + 千问跨期语义选篇 (select_daily_items)】
  ├─ 按分数从高到低遍历未读池，逐篇调用 fetch_full_text() 预拉取正文校验：
  │   · YouTube 视频自动通过 InnerTube Android 接口提取「完整简介章节大纲 + 完整口播字幕轨道」
  │   · 网页自动识别并剔除 404 页、Cloudflare 验证码页、Google News 跳转壳
  │   · 有效正文不足 400 字的标记为 status="insufficient_content" 自动跳过递补，杜绝模型对着标题硬编
  └─ 凑齐前 8 篇有完整正文的实料候选后，由千问（SELECT_PROMPT）对照最近已发的 15 篇历史记录，
     挑出「跨期语义不撞车 + 同日两篇视角互补（如 1 篇架构/机制长文 + 1 篇实操视频/案例）」的 2 篇。
        ↓
【Step 5 · 全文深度拆解 + 5 层架构定位 + 今日主线导读 (synthesize_product_insight)】
  基于最高 12,000 字原文/字幕，为每篇生成标准化结构，并生成串联两篇的「📌 今日主线导读」：
  · 🗺️ 架构坐标与上下游：定位在 Palantir 5 层架构（L1数据管道→L2本体与动作→L3 Agent编排与评测→L4交互应用 + L5安全治理）中的位置及上下游调用关系
  · 🔗 关联脉络：点明本篇与往期/同批已拆解模块是如何呼应递进的
  · 💡 一、功能本质与通俗解读：用通俗类比/对比讲透该功能到底解决什么问题（80% 重心还原 Palantir 真实产品逻辑）
  · 🔧 二、产品功能与机制拆解：拆出 3 条具体产品机制/交互设计细节（带具象业务对象例子）
  · 🔄 三、实际业务场景怎么用：还原「触发 → 界面交互 → 后台工具调用 → 业务系统写回」完整闭环
  · 🎯 四、对规划自研 AIP 的参考价值（20% 重心）：
      1) 【通用设计精髓与认知校准】：点出 Palantir 真实做法与常规直觉的差异，帮团队纠偏补盲
      2) 【对标框架落位与起步取舍】：轻量对照「数据本体底座(FDS)/Agent编排/运行部署(Stage)/上层应用」给出起步建议
        ↓
【Step 6 · 飞书群日报推送 + 飞书多维表格静默实时入库 (src/notify.py)】
  1) 向飞书群发送 1 条结构化富文本日报卡片，卡片最底部附带《Palantir 产品功能洞察库（飞书多维表格）》直达链接；
  2) 紧接着调用飞书多维表格工作流 Webhook，将当日 2 篇按 5 列字段（title / arch_layer / date / full_detail / url）
     静默写入飞书多维表格（新增 2 行记录，不触发额外群消息）。
        ↓
【Step 7 · 状态回写与 GitHub 仓库归档提交】
  将当日已发条目标记为 status="sent"，同步更新仓库内的 pool.json 与《Palantir产品功能洞察库.md》并自动 git push。
```

---

## 二、目录结构

```text
palantir-daily-brief/
├── .github/workflows/
│   └── daily.yml              # GitHub Actions 工作流（支持外部 API 触发与自动回写知识池）
├── src/
│   ├── fetch.py               # 八路中英文图文/视频抓取、工作日轮换搜索、YouTube 字幕与网页正文提取
│   ├── brief.py               # 候选池评分、正文实料校验、跨期语义选篇、5层架构拆解与 Markdown 归档
│   └── notify.py              # 飞书群富文本卡片推送 + 飞书多维表格 Webhook 静默实时写入
├── pool.json                  # 持久化产品洞察候选池与已发状态记录
├── Palantir产品功能洞察库.md     # 自动按 L1~L5 五层架构分类归档的往期产品功能拆解手册
├── 外部定时触发配置.md          # 外部定时触发（API workflow_dispatch）配置说明
├── requirements.txt           # Python 依赖（requests）
├── .env.example               # 环境变量模板
└── README.md
```

---

## 三、环境变量与 GitHub Secrets 说明

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 中配置：

| 变量名 | 必填 | 说明 |
| :--- | :--- | :--- |
| `LLM_API_KEY` | 是 | 阿里云百炼 DashScope API Key |
| `LLM_BASE_URL` | 否 | 默认 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | 否 | 默认 `qwen-flash` |
| `FEISHU_WEBHOOK` | 否 | 飞书群自定义机器人 Webhook（留空则仅打印预览日志，不消耗池中未读状态） |
| `FEISHU_SECRET` | 否 | 飞书机器人签名校验密钥（未开启签名校验可留空） |
| `FEISHU_BITABLE_WEBHOOK` | 否 | 飞书多维表格「新增记录」自动化工作流 Webhook（静默实时入库） |
| `FEISHU_BITABLE_URL` | 否 | 附在每日飞书报告底部的飞书多维表格知识库直达链接 |
| `DAILY_COUNT` | 否 | 每日精选篇数，默认 `2` |
