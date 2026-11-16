# Palantir AIP 产品深度洞察 (`palantir-daily-brief`)

面向规划自研 AIP 的产品团队：每个工作日 09:00，自动从技术专栏、YouTube 中英文科普/实操视频、推特（X）、开源研究与 Palantir 官方文档中筛选 **1~2 篇关于 Palantir 产品功能、设计机制与业务流落地的深度内容**，由千问（`qwen-flash`）提炼为结构化产品洞察推送至飞书群。

---

## 一、项目做了什么

### 1. 六路产品内容抓取（`src/fetch.py`）
不设短期新闻时效截断，围绕「把 Palantir 产品功能与设计逻辑讲清楚」抓取六个渠道：
- **YouTube 中英文视频（第三方科普/实操 + 官方演示）**：
  - 搜索中英文实操教程、白板架构拆解与官方 Demo（如 Ontology 建模实操、OSDK 全栈教程、AIP Logic 工作流搭建、Agent 与 Ontology 交互解析等）
  - 入选精读时，自动拉取视频详情页的**完整章节大纲（`shortDescription`）+ 字幕轨道实录（`captionTracks`）**
- **推特（X）产品与架构动态**：
  - 抓取 `@PalantirTech`、`@chadwahl`（Ontology 架构师）、`@PalantirVision` 关于 DevCon 新特性、Model Studio、Snapshots 评估、MCP 集成的推文
- **英文技术社区深度专栏**：
  - `Medium #palantir`、`Dev.to #palantir`、`HackerNews Algolia`（聚焦 Ontology、AIP、OAG 等技术讨论）
- **中英文产品架构定向搜索**：
  - 定向检索 `Palantir AIP 架构 / 本体论 / Ontology / workflow`，语法级排除 `-stock -NASDAQ -NYSE -shares`
- **Palantir 官方工程博客**：
  - `blog.palantir.com/feed`
- **开源深度研究与官方文档底座**：
  - GitHub 开源专题 `palantir-aip-study`（6 篇中文深度拆解 Markdown 全文）
  - Palantir AIP 官方核心文档（`/docs/foundry/aip/*` 12 个核心功能与安全治理模块）

**代码级硬过滤（`is_noise`）**：直接剔除纯股价涨跌、财报估值指标（如 Rule of 40、165% 续费率炒作、美股分析）、高管政治选举言论、招聘宣传贴。

---

### 2. 候选池评分与三层去重（`src/brief.py` + `pool.json`）

- **千问产品功能价值评分（0~10 分）**：
  - 对新发现的候选分批打分，并提取每篇所讲的**核心产品功能切面（`feature_focus`）**。
  - `≥ 7 分` 作为高价值产品洞察存入 `pool.json`（标记 `status: "unread"` 排队待发）；`< 7 分` 标记 `status: "rejected"` 淘汰。
- **三层去重机制**：
  1. **URL 永久去重**：所有进过 `pool.json` 的链接（无论已发还是淘汰）不再重复抓取、不再重复打分。
  2. **跨期功能点去重**：每日选篇时，将候选的 `feature_focus` 与最近已发送的 15 篇进行重合度比对，避免连续多天重复讲同一个已讲透的功能点。
  3. **同日互补去重**：当天入选的 2 篇之间要求功能切面不重复，且优先搭配不同来源（如 1 篇深度架构长文 + 1 篇实操视频或新功能拆解）。
- **正文有效长度校验**：
  - 入选当日推送前，先拉取全文（最高 12,000 字符）；若因目标站点反爬或无字幕导致有效正文不足 400 字符，自动跳过并递补下一篇，防止模型仅凭标题硬编。

---

### 3. 每日全文拆解与飞书推送（`src/notify.py`）

每篇高分资料拉取全文后，由千问按产品团队视角提炼为 4 个固定板块推送到飞书群：
1. **💡 功能本质与通俗解读**：用通俗类比/打比方讲清这个功能或概念到底是什么、解决什么痛点。
2. **🔧 产品功能与机制拆解**：3 条具体功能设计、模块配合或交互细节（带具象例子）。
3. **🔄 实际业务场景怎么用**：还原业务触发 → 界面交互 → 工具/动作调用 → 写回业务系统的完整流程。
4. **🎯 对我们规划自研 AIP 的参考价值**：2 条可借鉴的产品设计点或避坑启示 + **🔗 原文/原视频链接**。

**防重与安全保护**：
- **同日防重锁**：若当天（`sent_at == YYYY-MM-DD`）已成功推送过正式群，同一天后续重复触发会自动跳过。
- **未配 Webhook 不消耗库存**：当 `FEISHU_WEBHOOK` 留空时，仅更新 `pool.json` 并在日志输出预览，文章保持 `unread` 状态留在池中。

---

## 二、目录结构

```
palantir-daily-brief/
├── .github/workflows/
│   └── daily.yml              # GitHub Actions 工作流（支持外部定时 workflow_dispatch 触发）
├── src/
│   ├── fetch.py               # 六路内容源抓取、噪音硬过滤、文章/视频字幕全文提取
│   ├── brief.py               # 候选池管理、千问产品价值打分、功能点去重、全文洞察提炼
│   └── notify.py              # 飞书富文本卡片构建、同日防重锁、状态回写
├── pool.json                  # 持久化产品洞察候选池与已发状态记录
├── 外部定时触发配置.md          # 外部定时触发（API workflow_dispatch）配置说明
├── requirements.txt           # Python 依赖
└── .env.example               # 环境变量示例
```

---

## 三、环境变量与 GitHub Secrets

| 变量名 | 说明 |
| :--- | :--- |
| `LLM_API_KEY` | 阿里云百炼 API Key |
| `LLM_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | `qwen-flash` |
| `FEISHU_WEBHOOK` | 目标飞书群自定义机器人 Webhook（留空时仅打印日志预览，不消耗池内未读状态） |
| `FEISHU_SECRET` | 可选，飞书机器人签名校验密钥 |
