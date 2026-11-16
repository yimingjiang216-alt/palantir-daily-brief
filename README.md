# palantir-daily-brief

面向自研 AIP 产品团队的 Palantir 产品功能每日拆解与知识库沉淀工具。
每日自动抓取中英文图文与视频资源，筛选评分后挑选 **2~5 篇**跨架构层内容进行全文拆解，同步推送飞书群日报并写入飞书多维表格。

---

## 一、系统架构与处理流程

| 阶段 | 模块 | 处理逻辑 |
| :--- | :--- | :--- |
| **1. 定时触发** | `.github/workflows/daily.yml` | 每日 `09:00`（北京时间）由外部调度器调用 GitHub API `workflow_dispatch` 触发，启动前先校验 `pool.json` 同日防重锁（`sent_at == today`）。 |
| **2. 多源抓取** | `src/fetch.py` | 轮询 8 类中英文图文与视频渠道，执行 URL 归一化去重，并通过 `is_noise()` 过滤股价、财报、政治、招聘等非产品内容。 |
| **3. 评分入池** | `src/brief.py` → `update_candidate_pool()` | 仅对未入池的新 URL 按 15 条/批调用 `qwen-flash` 打分（0~10 分）：`>=7` 分标为 `unread` 入池排队，`<7` 分标为 `rejected` 永久跳过。 |
| **4. 选稿校验** | `src/brief.py` → `select_daily_items()` | 按分数排序并对 L1~L5 架构层做均衡采样，预拉取正文（YouTube 提取 InnerTube 字幕与章节，网页剔除 404/Cloudflare），凑齐 12 篇 `>=400` 字的候选后，由模型结合近期已发记录挑出 **2~5 篇**跨层互补内容。 |
| **5. 深度拆解** | `src/brief.py` → `synthesize_product_insight()` | 基于最高 12,000 字原文提炼四部分结构化洞察，按 URL 规则与模块权重词表校准 L1~L5 架构层，并提取每篇对应的原子级产品功能组件规格（同批次强制组件名去重）。 |
| **6. 双端分发** | `src/notify.py` | ① 发送飞书群富文本日报（超 24KB 自动拆分为上下篇）；② 调用多维表格自动化 Webhook 静默新增 2~5 条功能组件规格记录。 |
| **7. 状态归档** | `src/brief.py` → `mark_items_sent()` | 将当日条目更新为 `sent`、`bitable_synced=True`，生成按五层架构分类的 `Palantir产品功能洞察库.md`，并自动提交回 GitHub 仓库。 |

---

## 二、数据源列表

| 渠道类别 | 具体来源 | 抓取方式与提取内容 |
| :--- | :--- | :--- |
| **官方产品文档** | Palantir Foundry / AIP Docs（21 个核心模块） | 覆盖 Ontology、Action Types、Functions、Interfaces、Object Views、Permissioning、OSDK、AIP Logic、AIP Evals、Agent Studio、Workshop、Automate |
| **开源专题研究** | GitHub `palantir-aip-study`（6 篇中文架构章节） | 直拉仓库原始 Markdown 全文 |
| **YouTube 视频** | 中文科普（跟贝贝一起学习等）+ 英文实操 + 周一至周五按 5 大模块轮换检索 | 搜索页提取视频元数据，选中后通过 InnerTube Android 接口拉取完整简介章节与口播字幕轨道 |
| **X (Twitter)** | `@PalantirTech`、`@chadwahl`、`@PalantirVision`、`@ssankar` | Jina Reader 拉取时间线并按单条推文切分，提取真实 `/status/` 链接与正文 |
| **Substack 专栏** | 按模块关键词轮换检索 Palantir / Ontology / AIP 深度长文 | 提取 `/p/` 专栏正文 |
| **官方与技术社区** | `blog.palantir.com`、`Dev.to #palantir`、`Medium` 三标签、`Towards Data Science` | RSS 订阅解析，优先保留 `content:encoded` 完整长文 |
| **中文科技媒体** | 虎嗅 Palantir 专栏、36氪、InfoQ、量子位、极客公园、雷峰网、钛媒体、少数派 | RSS 订阅 + 关键词过滤 |
| **HackerNews** | Algolia API（`Palantir AIP` / `Palantir Ontology` / `Palantir Foundry`） | 提取高互动讨论帖及外链正文 |

---

## 三、五层架构坐标（L1 ~ L5）

所有日报条目与多维表格组件均归入以下 5 个标准架构层（由 `resolve_arch_layer()` 按「官方文档 URL 路径 → 标题模块专有词 3 倍权重 → 模型兜底」三级规则判定）：

| 架构层级 | 覆盖的 Palantir 核心模块 | 对应自研 AIP 方向 |
| :--- | :--- | :--- |
| `L1 数据接入与管道层` | Data Connection、Pipeline Builder、Sync / Connectors | 数据接入与治理底座 |
| `L2 本体与动作层` | Ontology、Object Types、Link Types、Object Views、Action Types、Functions | 数据与本体底座（AIP-FDS） |
| `L3 Agent 编排与评测层` | AIP Logic、Agent Studio、AIP Evals、LLM 工具调用与护栏 | Agent 编排与运行时（AIP-Agent） |
| `L4 交互应用与开发层` | Workshop、OSDK、Automate、Slate、前端组件与事件绑定 | 应用构建与开发套件 |
| `L5 安全治理与工程落地` | Markings 权限控制、PBAC/RBAC、Apollo 部署、FDE 驻场交付模式 | 安全治理与运行部署（AIP-Stage） |

---

## 四、双端输出结构

### 1. 飞书群日报（面向每日阅读）
- **📌 今日主线导读**：2~3 句话串联当日 2~5 篇内容的核心产品命题与跨层递进关系。
- **单篇拆解结构（每日 2~5 篇）**：
  - `🗺️ 架构位置与上下游`：所属 L1~L5 层级及与上下游模块的调用关系
  - `🔗 关联脉络`：与往期或同批模块的呼应关系
  - `💡 一、功能本质与通俗解读`：还原该功能解决的核心问题与机制本质（80% 重心）
  - `🔧 二、产品功能与机制拆解`：3 条具体产品机制、配置项或交互细节
  - `🔄 三、实际业务场景怎么用`：从触发、界面交互、工具调用到写回的完整闭环
  - `🎯 四、对我们规划自研 AIP 的参考价值`：`【通用设计精髓与认知校准】` + `【对标框架落位与起步取舍】`（20% 重心）
- **📚 底部知识库入口**：直达飞书多维表格《Palantir 5层产品功能洞察库》。

### 2. 飞书多维表格（面向 PRD 功能组件检索）
多维表格通过自动化工作流 Webhook 接收 JSON 并执行「新增记录」（不发群消息），每篇文章沉淀 1 条不重复的原子功能组件规格：

| 多维表格列名 | 字段类型 | Webhook JSON 键名 | 写入内容说明 |
| :--- | :--- | :--- | :--- |
| `功能组件` | 文本（主列） | `title` | 原子级功能组件名（如 `Action Type（动作类型）`、`Blocks（块状逻辑单元）`） |
| `架构层级` | 单选（L1~L5） | `arch_layer` | 精确匹配 `L1 数据接入与管道层` ~ `L5 安全治理与工程落地` 五个单选值 |
| `产品设计规格` | 多行文本 | `core_concept` | `🔧 【产品设计规格】`：输入参数/Schema、前端交互方式、后台执行与校验规则 |
| `自研对标参考` | 多行文本 | `aip_inspiration` | `🎯 【自研对标参考】`：对应自研模块落位、常规做法盲区与可直接借鉴的 PRD 功能点 |
| `规格详情` | 多行文本 | `full_detail` | 组件完整规格、业务场景闭环与来源文章汇总 |
| `推送日期` | 文本 | `date` | `YYYY-MM-DD` |
| `原文链接` | 超链接/文本 | `url` | 原始资料 URL |
| `我方采纳评估` | 单选 | — | 留空由产品团队人工评审（如 `🔥 必抄核心机制` / `📌 纳入排期参考`） |

---

## 五、目录结构

```text
palantir-daily-brief/
├── .github/workflows/
│   └── daily.yml                  # GitHub Actions 工作流（支持 workflow_dispatch 触发与状态回写）
├── src/
│   ├── fetch.py                   # 八路内容源抓取、噪音过滤、YouTube 字幕与网页正文提取
│   ├── brief.py                   # 候选池评分、跨层均衡选稿（2~5篇）、全文拆解、五层架构归档
│   └── notify.py                  # 飞书群富文本推送（含超长自动分片）+ 多维表格 Webhook 同步
├── pool.json                      # 候选池与已发状态持久化存储
├── Palantir产品功能洞察库.md         # 按 L1~L5 自动生成的 Markdown 知识库索引
├── 外部定时触发配置.md              # cron-job.org 外部定时触发配置说明
├── requirements.txt               # Python 依赖
├── .env.example                   # 本地环境变量模板
└── README.md
```

---

## 六、部署与运行配置

### 1. GitHub Actions Secrets
在仓库 `Settings -> Secrets and variables -> Actions` 中配置以下密钥：

| 变量名 | 必填 | 默认值 / 说明 |
| :--- | :---: | :--- |
| `LLM_API_KEY` | 是 | 阿里云百炼 DashScope API Key |
| `LLM_BASE_URL` | 否 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | 否 | `qwen-flash` |
| `FEISHU_WEBHOOK` | 是 | 飞书群自定义机器人 Webhook（留空则仅打印日志，不消耗 `unread` 队列） |
| `FEISHU_SECRET` | 否 | 飞书机器人签名密钥（未开启签名校验可留空） |
| `FEISHU_BITABLE_WEBHOOK` | 否 | 飞书多维表格「新增记录」自动化工作流 Webhook |
| `FEISHU_BITABLE_URL` | 否 | 附在群日报底部的飞书多维表格知识库链接 |
| `DAILY_MIN_COUNT` | 否 | 每日最少精选篇数，默认 `2`（重磅深度长文精读 2~3 篇） |
| `DAILY_MAX_COUNT` | 否 | 每日最多精选篇数，默认 `5`（多模块互补拆解最多 5 篇） |

### 2. 外部定时触发（`cron-job.org`）
- **请求地址**：`https://api.github.com/repos/yimingjiang216-alt/palantir-daily-brief/actions/workflows/daily.yml/dispatches`
- **请求方法**：`POST`
- **执行时间**：每日 `09:00`（`Asia/Shanghai`）
- **请求头**：
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer <GitHub PAT (repo + workflow)>`
  - `Content-Type: application/json`
- **请求体**：`{"ref":"main"}`

### 3. 手动触发与本地调试
- **GitHub Actions 手动运行**：进入 `Actions -> Palantir AIP 产品深度洞察 -> Run workflow`，支持两个可选参数：
  - `feishu_webhook_test`：填入测试群 Webhook 时仅向测试群发送，不修改 `pool.json` 状态、不写多维表格。
  - `force_run`：填 `true` 时忽略当日已发防重锁，强制加发一期。
- **本地运行**：
  ```bash
  pip install -r requirements.txt
  python src/notify.py
  ```
