# Palantir AIP 产品深度洞察工作流（palantir-daily-brief）

面向自研 AIP 产品团队的自动化竞品功能拆解与知识库沉淀系统，同时作为团队《产品协作 AI 工具方案》中 **P0 级「市场与产品洞察 Agent」的已落地工程样板**。

系统围绕 **「讲透 Palantir 产品功能机制、沉淀可复用 PRD 组件规格」** 展开，通过 **`On-the-Loop`（AI 全自动巡检、过滤、拆解、入库）** 与 **`In-the-Loop`（产品经理在多维表格看板执行采纳评估与需求转化）** 的人机协同模式，每日 `09:00` 自动完成从多源信息采集到结构化知识资产归档的完整闭环。

---

## 一、设计定位与人机协同机制（On-the-Loop $\rightarrow$ In-the-Loop）

针对产品团队在竞品跟踪与架构规划中面临的**信息分散耗时、水文噪音多、AI 摘要易产生幻觉、读完难以转化为具体 PRD 功能设计**四大痛点，本系统在工程上确立了明确的 `On-the-Loop` 与 `In-the-Loop` 边界：

| 核心痛点与治理维度 | 系统工程实现机制 | 人机协同模式定位 |
| :--- | :--- | :--- |
| **1. 信息入口分散、人工检索耗时** | 每日 `09:00` 自动轮询 8 大类中英文图文与视频渠道（官方文档、GitHub 专题、YouTube 字幕、X 核心账号、Substack、Medium、技术社区与中文科技媒体），URL 归一化入池。 | **`On-the-Loop`**<br>AI 全自动定时巡检，无需人工触发或搜集 |
| **2. 财报/股价/公关水文干扰** | **双层漏斗过滤**：① `is_noise()` 词表硬过滤股价、财报估值、政治选举、招聘宣传；② LLM 按「产品功能洞察价值（0~10分）」评分，`< 7` 分标记为 `rejected` 永久淘汰，`>= 7` 分方可入池排队。 | **`On-the-Loop`**<br>AI 自动清洗去噪，异常低分自动拦截 |
| **3. 模型幻觉与来源不可溯** | **正文实料硬校验**：选稿阶段预拉取全文（YouTube 经 InnerTube 接口提取完整口播字幕与章节，网页自动剔除 404/Cloudflare 验证页），有效正文 `< 400` 字不予入选，杜绝模型仅凭标题编造内容；所有输出强绑定原始 URL。 | **`On-the-Loop`**<br>代码硬规则保障输入实料与原文可溯源 |
| **4. 内容同质化与架构层偏科** | **5 层去重锁 + 跨层均衡采样**：建立「同日触发锁 $\rightarrow$ URL 永久状态锁 $\rightarrow$ 双字符重合度初筛 $\rightarrow$ 近期已发语义去重 $\rightarrow$ 多维表格组件名跨期去重」五重约束；候选短名单限制单一架构层上限，并在命中 9~10 分重磅长文时自动将篇数收敛为 **2~3 篇**（常规碎片日最多 **5 篇**）。 | **`On-the-Loop`**<br>AI 主编策略自动控量、控质、控结构均衡 |
| **5. 读完停留在概念、难以转化为 PRD** | **双轨制交付**：<br>① **飞书群日报**：还原文章脉络、产品机制与客户业务场景闭环（80% 重心）+ 自研认知校准（20% 重心）；<br>② **飞书多维表格**：每篇单独剥离出 1 个**原子级功能组件规格**（含输入参数/Schema、前端交互、后台校验规则与自研对标动作），静默写入 L1~L5 架构看板。 | **`On-the-Loop` $\rightarrow$ `In-the-Loop` 交接**<br>AI 自动入库（On），产品经理在表格「**我方采纳评估**」列打标拍板并转入 PRD 撰写（In） |

---

## 二、系统处理流水线（7 阶段闭环）

| 阶段 | 核心模块与函数 | 关键处理逻辑与工程约束 |
| :--- | :--- | :--- |
| **Stage 1 · 外部定时调度** | `.github/workflows/daily.yml`<br>`notify.main()` | 每日 `09:00`（`Asia/Shanghai`）由外部调度器调用 GitHub API `workflow_dispatch` 触发；启动后首先检查 `pool.json` 同日防重锁（`sent_at == today`），防止重复发送。 |
| **Stage 2 · 八路多源抓取** | `src/fetch.py`<br>`fetch_all_candidates()` | 并发/顺序拉取 8 类中英文图文与视频源（YouTube 搜索词按周一至周五分 5 大模块轮换），执行 URL 规范化与 `is_noise()` 非产品噪音剔除。 |
| **Stage 3 · 价值评分入池** | `src/brief.py`<br>`update_candidate_pool()` | 已存在于 `pool.json` 的 URL 直接跳过；新候选按 15 条/批调用千问模型评分并提取一句话功能切面（`feature_focus`）：`>= 7` 分标为 `unread` 入池，`< 7` 分标为 `rejected`。 |
| **Stage 4 · 实料校验与选稿** | `src/brief.py`<br>`select_daily_items()` | 按评分排序并对 `L1~L5` 做跨层均衡采样（单层初筛最多 4 篇），逐篇调用 `fetch_full_text()` 校验正文 `>= 400` 字（连续 3 次抓取失败才标为 `insufficient_content`，防止网络抖动误杀）；凑齐 12 篇实料候选后，由模型结合近期已发记录选出 **2~5 篇**（命中 9~10 分万字长文时由 `_cap_by_quality()` 强制收敛为 **2~3 篇**）。 |
| **Stage 5 · 四层拆解与组件提取** | `src/brief.py`<br>`synthesize_product_insight()` | 基于最高 12,000 字原文提炼结构化洞察，通过 `resolve_arch_layer()` 三级硬规则校准所属 `L1~L5` 架构层；同时结合往期与同批已用组件列表，提取不重复的原子级功能组件规格（`feature_specs`），并生成串联全篇的「今日主线导读」。 |
| **Stage 6 · 双端分发同步** | `src/notify.py`<br>`send_feishu()`<br>`sync_to_feishu_bitable()` | ① 向飞书群推送富文本日报卡片（单卡 JSON 超 `24KB` 时自动拆分为上、下两篇发送）；<br>② 调用飞书多维表格自动化 Webhook 静默新增组件规格记录（带 `bitable_synced` 永久防重锁）。 |
| **Stage 7 · 状态持久化归档** | `src/brief.py`<br>`mark_items_sent()`<br>`update_knowledge_base_md()` | 将当日已发条目标记为 `status="sent"`、`bitable_synced=True`，重新生成按五层架构分类的 `Palantir产品功能洞察库.md`，由 GitHub Actions 自动提交回写仓库。 |

---

## 三、数据源矩阵（8 类渠道）

| 渠道类别 | 具体来源与覆盖范围 | 正文提取方式 |
| :--- | :--- | :--- |
| **1. 官方产品文档** | Palantir Foundry / AIP Docs（21 个核心功能模块：Ontology、Action Types、Functions、Interfaces、Object Views、Permissioning、OSDK、AIP Logic、AIP Evals、Agent Studio、Workshop、Automate） | Jina Reader / 直连提取文档正文，自动识别并拦截 404 页 |
| **2. 开源专题研究** | GitHub `palantir-aip-study`（6 篇中文架构深度解析章节） | GitHub Raw 接口直拉完整 Markdown 原文 |
| **3. YouTube 视频** | 中文深度科普（跟贝贝一起学习等）+ 英文实操拆解 + 周一至周五按 5 大模块轮换检索 | 搜索页提取视频元数据；选中后通过 InnerTube Android 接口拉取完整视频简介、章节时间戳与口播字幕轨道 |
| **4. X (Twitter)** | `@PalantirTech`（官方与 DevCon 动态）、`@chadwahl`（Ontology 架构师）、`@PalantirVision`（AIP/MCP 拆解）、`@ssankar`（CTO 产品思考） | 时间线按单条推文切分，提取真实 `/status/` 链接与长推文内容 |
| **5. Substack 专栏** | 按模块关键词轮换检索 Palantir / Ontology / AIP 深度架构专栏 | 剥离嵌套图片标记后提取 `/p/` 专栏长文 |
| **6. 官方与英文社区** | `blog.palantir.com`、`Dev.to #palantir`、`Medium`（3 个核心 Tag）、`Towards Data Science` | RSS 订阅解析，优先保留 `content:encoded` 完整全文并持久化入池 |
| **7. 中文科技媒体** | 虎嗅 Palantir 专栏、36氪、InfoQ、量子位、极客公园、雷峰网、钛媒体、少数派 | RSS 订阅 + Palantir / 本体 / AIP 关键词过滤 |
| **8. HackerNews** | Algolia Search API（检索 `Palantir AIP` / `Palantir Ontology` / `Palantir Foundry` 高赞技术讨论） | 提取讨论帖及关联外链正文 |

---

## 四、五层架构坐标体系（L1 ~ L5）

为确保拆解内容与自研 AIP 架构模块精准对齐，系统定义了 5 个标准架构层，并通过 `resolve_arch_layer()` 执行**三级确定性判定**（① 官方文档 URL 路径优先匹配 $\rightarrow$ ② 洞察标题与功能标签模块专有词 3 倍权重匹配 $\rightarrow$ ③ 模型输出兜底）：

| 标准架构层级 | 覆盖的 Palantir 核心模块 | 对应自研 AIP 规划方向 |
| :--- | :--- | :--- |
| **`L1 数据接入与管道层`** | Data Connection、Pipeline Builder、Sync / Connectors、多源异构数据清洗与同步 | 数据接入与管道底座 |
| **`L2 本体与动作层`** | Ontology、Object Types、Link Types、Object Views、Interfaces、Action Types、Functions | 数据与本体底座（`AIP-FDS`） |
| **`L3 Agent 编排与评测层`** | AIP Logic、Agent Studio、AIP Evals、LLM 工具调用、可控性旋钮与回归测试套件 | Agent 编排与运行时（`AIP-Agent`） |
| **`L4 交互应用与开发层`** | Workshop、OSDK（Ontology SDK）、Automate、Slate、前端低代码组件与事件触发 | 交互应用构建与开发套件 |
| **`L5 安全治理与工程落地`** | Markings 细粒度权限穿透、PBAC/RBAC、零数据留存、人机协同审批、Apollo 部署与 FDE 交付模式 | 安全治理与运行部署底座（`AIP-Stage`） |

---

## 五、双端交付物规格

### 1. 飞书群日报卡片（面向团队每日精读）
- **📌 今日主线导读**：2~3 句话提炼当日入选内容共同围绕的产品命题及跨架构层递进逻辑。
- **单篇四段式拆解（每日 2~5 篇，重磅报告日 2~3 篇）**：
  - `🗺️ 架构位置与上下游`：明确所属 `L1~L5` 层级及与上下游模块的调用关系。
  - `🔗 关联脉络`：说明与往期或同批已拆解模块的呼应递进关系。
  - `💡 一、功能本质与通俗解读`：用直观类比还原该功能解决的核心业务与工程问题（占 80% 篇幅重心）。
  - `🔧 二、产品功能与机制拆解`：拆出 3 条具体产品机制、配置项或界面交互细节（带具体业务对象示例）。
  - `🔄 三、实际业务场景怎么用`：还原「触发条件 $\rightarrow$ 界面交互 $\rightarrow$ 后台工具/本体调用 $\rightarrow$ 业务写回」完整闭环。
  - `🎯 四、对我们规划自研 AIP 的参考价值`（占 20% 篇幅重心）：
    - `【通用设计精髓与认知校准】`：指出 Palantir 真实产品机制与常规直觉的差异；
    - `【对标框架落位与起步取舍】`：结合自研框架给出模块落位与 MVP 阶段取舍建议。
- **📚 底部知识库直达链接**：一键跳转飞书多维表格《Palantir 5层产品功能洞察库》。

### 2. 飞书多维表格《Palantir 5层产品功能洞察库》（面向 PRD 组件级检索与评审）
通过飞书多维表格自动化工作流（触发器：收到 Webhook $\rightarrow$ 动作：新增记录，不发群消息），将每篇文章提炼出的原子功能组件规格静默写入表格：

| 多维表格列名 | 字段类型 | Webhook JSON 键名 | 字段内容与用途说明 |
| :--- | :--- | :--- | :--- |
| **`功能组件`** | 文本（主列） | `title` | 原子级功能组件名称（如 `Action Type（受控写操作）`、`Allowed Markings Allowlist（允许标记白名单）`） |
| **`架构层级`** | 单选（L1~L5） | `arch_layer` | 严格匹配 `L1 数据接入与管道层` ~ `L5 安全治理与工程落地` 五个单选选项，驱动看板分泳道展示 |
| **`产品设计规格`** | 多行文本 | `core_concept` | `🔧 【产品设计规格】`：配置该组件所需的输入参数/Schema、前端交互方式、后台执行与校验规则 |
| **`自研对标参考`** | 多行文本 | `aip_inspiration` | `🎯 【自研对标参考】`：对应自研模块落位、常规设计盲区及撰写 PRD 时可直接复用的功能设计点 |
| **`规格详情`** | 多行文本 | `full_detail` | 组件产品设计规格、自研对标参考与来源文章的完整汇总卡片 |
| **`推送日期`** | 文本 | `date` | 入库日期（`YYYY-MM-DD`） |
| **`原文链接`** | 文本/链接 | `url` | 原始参考资料 URL，支持一键溯源核验 |
| **`我方采纳评估`** | 单选 | *人工维护（In-the-Loop）* | 由产品经理在看板中评审打标（如 `🔥 必抄核心机制` / `📌 纳入排期参考` / `💡 仅作理念参考`） |

---

## 六、仓库目录结构

```text
palantir-daily-brief/
├── .github/workflows/
│   └── daily.yml                  # GitHub Actions 工作流（支持外部 API 触发、25 分钟超时保护与状态自动回写）
├── src/
│   ├── fetch.py                   # 八路内容源抓取、噪音过滤、YouTube InnerTube 字幕与网页正文提取
│   ├── brief.py                   # 候选池评分、跨层均衡选稿、质量收敛控制、四层拆解、组件去重与归档
│   └── notify.py                  # 飞书群富文本卡片推送（含 24KB 自动分片）+ 飞书多维表格 Webhook 同步
├── pool.json                      # 持久化候选池（记录 status / score / feature_focus / sent_at / bitable_synced）
├── Palantir产品功能洞察库.md         # 按 L1~L5 五层架构自动归档生成的 Markdown 历史索引手册
├── 外部定时触发配置.md              # cron-job.org 外部定时触发配置文档
├── requirements.txt               # Python 依赖（requests）
├── .env.example                   # 本地调试环境变量模板
└── README.md
```

---

## 七、部署与运行配置

### 1. GitHub Actions Secrets 配置
在仓库 `Settings -> Secrets and variables -> Actions` 中配置以下环境变量：

| 变量名 | 必填 | 默认值 / 配置说明 |
| :--- | :---: | :--- |
| `LLM_API_KEY` | 是 | 阿里云百炼 DashScope API Key（或兼容 OpenAI 接口的密钥） |
| `LLM_BASE_URL` | 否 | 默认 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | 否 | 当前生产配置为 `qwen4-max`（代码默认兜底为 `qwen-flash`） |
| `FEISHU_WEBHOOK` | 是 | 正式飞书群自定义机器人 Webhook（留空则仅在日志打印预览，不消耗 `unread` 队列） |
| `FEISHU_SECRET` | 否 | 飞书机器人签名校验密钥（未开启签名校验可留空） |
| `FEISHU_BITABLE_WEBHOOK` | 否 | 飞书多维表格「新增记录」自动化工作流 Webhook |
| `FEISHU_BITABLE_URL` | 否 | 附在每日群日报底部的飞书多维表格知识库直达链接 |
| `DAILY_MIN_COUNT` | 否 | 每日最少精选篇数，默认 `2`（命中 9~10 分重磅长文时自动收敛为 `2~3` 篇） |
| `DAILY_MAX_COUNT` | 否 | 每日最多精选篇数，默认 `5` |

### 2. 外部定时触发配置（`cron-job.org`）
为避免 GitHub Actions 内置 `schedule` 的排队延迟，生产环境由 `cron-job.org` 每日准点调用 GitHub REST API 触发：
- **URL**：`https://api.github.com/repos/yimingjiang216-alt/palantir-daily-brief/actions/workflows/daily.yml/dispatches`
- **请求方法**：`POST`
- **执行计划**：每日 `09:00`（时区：`Asia/Shanghai`）
- **Headers**：
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer <GitHub PAT (需具备 repo 与 workflow 权限)>`
  - `Content-Type: application/json`
- **Request Body**：`{"ref":"main"}`

### 3. 手动触发与调试模式
在 GitHub 仓库 `Actions -> Palantir AIP 产品深度洞察 -> Run workflow` 中支持带参数手动运行：
- `feishu_webhook_test`：填入测试群 Webhook 时进入 `TEST_MODE`，仅向测试群发送卡片，**不修改 `pool.json` 未读状态、不写入飞书多维表格**。
- `force_run`：填 `true` 时跳过当日 `sent_at == today` 防重锁，强制加发一期。
