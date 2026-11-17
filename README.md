# palantir-daily-brief

Palantir AIP 产品功能每日抓取、拆解与飞书推送脚本。
每天定时抓取中英文图文与视频资源，经评分筛选后挑出 2~5 篇内容做全文提炼，推送到飞书群并同步写入飞书多维表格。

---

## 一、处理流程

| 步骤 | 代码位置 | 实际执行逻辑 |
| :--- | :--- | :--- |
| **1. 同日防重检查** | `src/notify.py` → `main()` | 启动时读取 `pool.json`，若已存在 `status == "sent"` 且 `sent_at == 当天日期` 的记录（且未开启 `FORCE_RUN`），直接退出。 |
| **2. 多源抓取与过滤** | `src/fetch.py` → `fetch_all_candidates()` | 轮询 8 类渠道，对 URL 做归一化去重，并通过 `is_noise()` 过滤股价、财报、政治、招聘等非产品内容。 |
| **3. 评分入池** | `src/brief.py` → `update_candidate_pool()` | 跳过已在 `pool.json` 中的 URL；对新条目按 15 条/批调用大模型打分（0~10 分）并提取 `feature_focus`：`>= 7` 分标为 `unread` 入池，`< 7` 分标为 `rejected` 跳过。 |
| **4. 正文校验与选稿** | `src/brief.py` → `select_daily_items()` | 按分数从高到低遍历未读池，同属一个架构层的候选最多取 4 篇进入初筛。每篇调用 `fetch_full_text()` 拉取正文，不足 400 字则跳过并累加 `fetch_fail_count`，累计 3 次才将状态改为 `insufficient_content`；抓取成功则清零该计数。凑够 12 篇有效候选后，把近期 20 篇已发记录和当前架构层一并交给模型，由模型输出选中的序号数组。若模型给出的序号数少于 `DAILY_MIN_COUNT`（默认 2），按「优先不同架构层、再优先不同来源」的顺序补齐至 `DAILY_COUNT`（默认 3）。最后经 `_cap_by_quality()` 收敛：前 2 篇均为 10 分且正文合计 12000 字以上时只留 2 篇；前 3 篇中至少 2 篇达到 9 分，或前 3 篇正文合计 9000 字以上时只留 3 篇；其余情况保留模型给出的原数量，最多不超过 `DAILY_MAX_COUNT`（默认 5）。 |
| **5. 全文拆解与组件提取** | `src/brief.py` → `synthesize_product_insight()` | 基于最高 12,000 字原文生成四段式拆解，按 `resolve_arch_layer()` 判定所属 L1~L5 架构层，提取 1 条不与往期及同批重复的原子功能组件规格（`feature_specs`），并由 `generate_daily_lead()` 生成今日导读。 |
| **6. 飞书推送与写表** | `src/notify.py` → `send_feishu()` / `sync_to_feishu_bitable()` | ① 发送飞书群 `post` 富文本消息（JSON 超过 24KB 时自动拆为上下两篇发送）；② 调用飞书多维表格自动化 Webhook 写入组件规格记录。 |
| **7. 状态回写归档** | `src/brief.py` → `mark_items_sent()` | 将当日条目更新为 `status="sent"`、`bitable_synced=True`，重新生成 `Palantir产品功能洞察库.md`，由 GitHub Actions 提交回仓库。 |

---

## 二、数据源

| 渠道类别 | 具体来源 | 正文提取方式 |
| :--- | :--- | :--- |
| **官方产品文档** | Palantir Foundry / AIP Docs（21 个模块：Ontology、Action Types、Functions、Interfaces、Object Views、Permissioning、OSDK、AIP Logic、AIP Evals、Agent Studio、Workshop、Automate） | Jina Reader / 直连提取正文，拦截 404 与验证码页 |
| **GitHub 专题** | `palantir-aip-study`（6 篇中文架构解析章节） | 拉取 GitHub Raw Markdown 原文 |
| **YouTube 视频** | 中文科普（跟贝贝一起学习等）+ 英文实操 + 周一至周五按 5 大模块轮换搜索 | 搜索页提取视频信息；选中后通过 InnerTube Android 接口提取视频简介、章节与字幕轨道 |
| **X (Twitter)** | `@PalantirTech`、`@chadwahl`、`@PalantirVision`、`@ssankar` | Jina Reader 拉取时间线并按单条推文切分，提取 `/status/` 链接与正文 |
| **Substack 专栏** | 按模块关键词轮换搜索 Palantir / Ontology / AIP 文章 | 提取 `/p/` 文章正文 |
| **英文技术社区** | `blog.palantir.com`、`Dev.to #palantir`、`Medium`（3 个标签）、`Towards Data Science` | RSS 解析，优先保留 `content:encoded` 全文 |
| **中文科技媒体** | 虎嗅 Palantir 搜索、36氪、InfoQ、量子位、极客公园、雷峰网、钛媒体、少数派 | RSS 订阅 + 关键词过滤 |
| **HackerNews** | Algolia API（搜索 `Palantir AIP` / `Palantir Ontology` / `Palantir Foundry`） | 提取高互动讨论帖与外链正文 |

---

## 三、五层架构分类（L1 ~ L5）

`resolve_arch_layer()` 按「官方文档 URL 路径规则 → 标题与标签专有词 3 倍权重匹配 → 模型输出兜底」三级规则，将每篇内容与功能组件归入以下 5 层之一：

| 架构层级 | 覆盖的 Palantir 模块 |
| :--- | :--- |
| `L1 数据接入与管道层` | Data Connection、Pipeline Builder、Connectors / Sync |
| `L2 本体与动作层` | Ontology、Object Types、Link Types、Object Views、Interfaces、Action Types、Functions |
| `L3 Agent 编排与评测层` | AIP Logic、Agent Studio、AIP Evals、LLM 工具调用与评测套件 |
| `L4 交互应用与开发层` | Workshop、OSDK、Automate、Slate、前端组件与事件绑定 |
| `L5 安全治理与工程落地` | Markings 权限控制、PBAC/RBAC、零数据留存、人机审批、Apollo、FDE 模式 |

---

## 四、输出格式

### 1. 飞书群消息（`msg_type: "post"`）
- `📌 今日主线导读`：串联当日 2~5 篇内容的导读。
- 单篇拆解结构：
  - `【洞察 N · L1~L5 层级 · 功能标签】标题`
  - `🗺️ 架构位置与上下游`
  - `🔗 关联脉络`
  - `💡 一、功能本质与通俗解读`
  - `🔧 二、产品功能与机制拆解`（3 条）
  - `🔄 三、实际业务场景怎么用`
  - `🎯 四、对我们规划自研 AIP 的参考价值`（2 条：`【通用设计精髓与认知校准】`、`【对标框架落位与起步取舍】`）
  - `🔗 原文来源`
- `📚 全量架构知识库`：底部附飞书多维表格链接。

### 2. 飞书多维表格 Webhook 字段映射
每次运行向 `FEISHU_BITABLE_WEBHOOK` 发送 POST JSON，每篇文章写入 1 条功能组件记录：

| 多维表格列名 | Webhook JSON 键名 | 写入内容 |
| :--- | :--- | :--- |
| `功能组件` | `title` | 原子功能组件名称（`feature_specs[].component_name`） |
| `架构层级` | `arch_layer` | `L1 数据接入与管道层` ~ `L5 安全治理与工程落地` |
| `产品设计规格` | `core_concept` | 输入参数/Schema、前端交互、后台执行与校验规则（`palantir_spec`） |
| `自研对标参考` | `aip_inspiration` | 对应模块落位与可复用的功能设计点（`our_action`） |
| `规格详情` | `full_detail` | 产品设计规格 + 自研对标参考 + 来源文章汇总文本 |
| `推送日期` | `date` | `YYYY-MM-DD` |
| `原文链接` | `url` | 原始文章/视频 URL |

---

## 五、目录结构

```text
palantir-daily-brief/
├── .github/workflows/
│   └── daily.yml                  # GitHub Actions 工作流
├── src/
│   ├── fetch.py                   # 多源抓取、噪音过滤、YouTube 字幕与网页正文提取
│   ├── brief.py                   # 评分入池、选稿校验、全文拆解、架构层判定与 Markdown 归档
│   └── notify.py                  # 飞书群消息推送与飞书多维表格 Webhook 同步
├── pool.json                      # 候选池与已发状态记录
├── Palantir产品功能洞察库.md         # 按 L1~L5 自动生成的历史拆解归档文档
├── 外部定时触发配置.md              # cron-job.org 定时调用 GitHub API 说明
├── requirements.txt               # Python 依赖（requests）
├── .env.example                   # 环境变量模板
└── README.md
```

---

## 六、配置与运行

### 1. 环境变量 / GitHub Secrets

| 变量名 | 必填 | 默认值 / 说明 |
| :--- | :---: | :--- |
| `LLM_API_KEY` | 是 | OpenAI 兼容接口 API Key（如阿里云百炼 DashScope） |
| `LLM_BASE_URL` | 否 | 默认 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | 否 | 模型名称（代码默认 `qwen-flash`，可在 Secrets 中覆盖为 `qwen4-max` 等） |
| `FEISHU_WEBHOOK` | 是 | 飞书群自定义机器人 Webhook（留空则仅打印日志，不修改 `pool.json` 状态） |
| `FEISHU_SECRET` | 否 | 飞书机器人签名校验密钥 |
| `FEISHU_BITABLE_WEBHOOK` | 否 | 飞书多维表格自动化工作流 Webhook |
| `FEISHU_BITABLE_URL` | 否 | 附在群消息底部的飞书多维表格链接 |
| `DAILY_MIN_COUNT` | 否 | 每日最少选稿篇数，默认 `2` |
| `DAILY_MAX_COUNT` | 否 | 每日最多选稿篇数，默认 `5` |

### 2. 定时与手动触发
- **外部定时触发**：通过 `cron-job.org` 每日 `09:00`（`Asia/Shanghai`）向 `https://api.github.com/repos/yimingjiang216-alt/palantir-daily-brief/actions/workflows/daily.yml/dispatches` 发送 `POST {"ref":"main"}`。
- **GitHub Actions 手动运行**：支持 `feishu_webhook_test`（仅发测试群，不改 `pool.json`、不写多维表格）与 `force_run`（填 `true` 跳过同日防重检查）。
- **本地运行**：
  ```bash
  pip install -r requirements.txt
  python src/notify.py
  ```
