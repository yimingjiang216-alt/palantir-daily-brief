# Palantir AIP 产品功能洞察库（按架构模块归档）

> 本文档由每日推送任务自动维护更新，按 Palantir **5 层产品架构坐标**归档每一期拆解过的产品功能、核心机制与自研 AIP 启示，方便产品团队按模块查阅。

## 🗺️ 全局 5 层产品架构导航

```
[L4 交互应用与开发层]  Workshop 操作台  |  Ontology SDK (OSDK)  |  Automate 自动触发器
         ↑ 调用                     ↑ 读写                              ↑ 唤醒
[L3 Agent 编排与评测]  AIP Logic (块状工具编排)  |  Agent Studio  |  AIP Evals (快照评测)
         ↑ 查询对象 & 申请执行 Action
[L2 本体与动作层]      Object / Property / Link (数字孪生名词)  +  Action Types / Functions (受控写回动词)
         ↑ 语义映射                                                     ↓ Webhook 写回外部 ERP/SAP
[L1 数据接入与管道层]  Data Connection (多模态连接器)  |  Pipeline Builder (批流一体清洗)
──────────────────────────────────────────────────────────────────────────────────────────
[L5 安全治理与落地范式] Markings 细粒度权限穿透  |  可解释审计追踪  |  FDE 驻场工程孵化模式
```

## 📅 已推送洞察总览表（共 27 篇）

| 推送日期 | 架构层级 | 洞察标题 | 核心功能切面 | 来源 |
| :--- | :--- | :--- | :--- | :--- |
| 2026-11-26 | L5 安全治理与工程落地 | **AIP安全架构：第三方模型零留存与区域端点路由** |  | [Palantir AIP 官方文档](https://www.palantir.com/docs/foundry/aip/aip-security/) |
| 2026-11-26 | L5 安全治理与工程落地 | **BYOM：自带模型统一接入与权限解耦** | 多模型接入（BYOM）与模型路由管理：开源/自托管模型与平台内置模型的统一调度能力 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/aip/bring-your-own-model) |
| 2026-11-26 | L5 安全治理与工程落地 | **FDE模式：驻场判断力如何沉淀为产品资产** |  | [GitHub 深度专题 (palantir-aip-study)](https://github.com/wwwweeia/palantir-aip-study/blob/main/02-fde-forward-deployed-engineer.md) |
| 2026-11-25 | L3 Agent 编排与评测层 | **AIP Evals：用测试集验收 AI 函数再上线** | AIP 核心模块分工：AIP Logic、Agent Studio、Assist、Evals、Workflow Builder 的功能边界与协作逻辑 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/aip/aip-features) |
| 2026-11-25 | L5 安全治理与工程落地 | **三档路径决策：按场景复杂度选AI落地深度** |  | [GitHub 深度专题 (palantir-aip-study)](https://github.com/wwwweeia/palantir-aip-study/blob/main/04-action-guide-domestic-ai.md) |
| 2026-11-24 | L3 Agent 编排与评测层 | **Agent Stack：会话持久化与类型化上下文驱动多参与者协作** | AIP Agent Stack 的工具封装体系：Ontology 查询、Action 执行与函数工具的分层集成 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/aip/agent-stack) |
| 2026-11-24 | L5 安全治理与工程落地 | **Object Permissioning：Schema与数据双层权限隔离** | Object Permissioning 支持对象、属性与链接级别的细粒度权限控制与多数据源安全策略 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/object-permissioning/overview) |
| 2026-11-24 | L5 安全治理与工程落地 | **案件工作流：Agent串联多步骤消除人工交接** | Citi Wealth 用 AIP 重构财富管理案件处理流程（9天→秒级），展示 Agent 驱动的端到端业务工作流与效率量化 | [YouTube 模块深挖·AIPCon客户真机Demo (Palantir)](https://www.youtube.com/watch?v=IZRCw5WnJm8) |
| 2026-11-23 | L3 Agent 编排与评测层 | **Agentic Runtime：Agent权限按三重身份动态求交** | Agentic Runtime 安全机制：详解生产环境中 AI Agent 的权限隔离、行为审计与运行时安全控制策略 | [Medium Palantir AIP 专栏](https://blog.palantir.com/securing-agents-in-production-agentic-runtime-1-5191a0715240?source=rss------palantir_aip-5) |
| 2026-11-23 | L2 本体与动作层 | **Ontology单对象：多界面只读同一份房产记录** | 基于本体原生设计解决地址语义歧义问题，构建消费者级房地产应用的实战案例 | [Medium Palantir Foundry 专栏](https://medium.com/@hr_52458/building-consumer-grade-applications-on-palantir-foundry-an-ontology-native-real-estate-product-4f5a48d2ea13?source=rss------palantir_foundry-5) |
| 2026-11-22 | L3 Agent 编排与评测层 | **Workflow Lineage：AIP执行链路追踪与生产可观测** |  | [Palantir AIP 官方文档](https://www.palantir.com/docs/foundry/aip/aip-observability/) |
| 2026-11-22 | L3 Agent 编排与评测层 | **Trace Curation：生产trace入本体转微调训练集** | Model Studio 中的微调能力与生产级 trace 收集机制，实现企业对 AI 模型训练过程的掌控 | [X @PalantirTech (官方产品与DevCon动态)](https://x.com/PalantirTech/status/2121278958683500549) |
| 2026-11-22 | L1 数据接入与管道层 | **Incremental Transforms：增量只读新增行，版本变更强制全量重算** | Legacy ETL 迁移至 Foundry 时的增量处理、模式演进与无停机验证策略 | [Dev.to Palantir 技术专栏](https://dev.to/kaviwrites/migrating-legacy-etl-to-palantir-foundry-incremental-transforms-schema-evolution-and-18lm) |
| 2026-11-21 | L4 交互应用与开发层 | **Workshop：Object层驱动的人机协同操作应用构建器** | Workshop 如何将 Ontology 视图、AIP Logic 推荐结果与 Action 按钮整合为一线业务员的人机协同操作界面 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/workshop/overview) |
| 2026-11-21 | L4 交互应用与开发层 | **Automate：条件持续监测驱动动作与Logic自动执行** | Automate 的事件驱动机制：基于 Ontology 状态变化或定时条件触发 AIP Logic 执行与业务动作 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/automate/overview) |
| 2026-11-21 | L3 Agent 编排与评测层 | **AIP Evals：用测试集与裁判模型量化LLM函数输出** | AIP Evals 教程：对 LLM Function/Agent/抽取器构建测试集并量化打分的完整流程 | [YouTube 模块深挖·AIP Evals评测与权限治理 (LearnWithBeibei)](https://www.youtube.com/watch?v=79x-Xf0VZ4Y) |
| 2026-11-20 | L3 Agent 编排与评测层 | **Guideline Evaluation：自动校验医疗必要性并生成申诉信** | AIPCon 8 企业 AI 未来愿景演示：揭示 AIP 如何通过统一语义空间（Unified Namespace）实现跨系统智能协同 | [Medium Palantir AIP 专栏](https://blog.palantir.com/inside-the-aipcon-8-demos-redefining-the-future-of-enterprise-ai-a0a740fe44ce?source=rss------palantir_aip-5) |
| 2026-11-20 | L3 Agent 编排与评测层 | **Chatbot Studio：检索上下文与工具白名单构建可溯源Agent** | Agent Studio 中基于 Ontology 上下文检索与 Action 工具调用权限配置的可解释性 Agent 构建机制 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/agent-studio/overview) |
| 2026-11-20 | L4 交互应用与开发层 | **OSDK：本体Schema编译为类型安全SDK供外部应用调用** | OSDK 将 Ontology 对象查询、Action 触发与 AI 函数封装为外部应用可调用的标准 SDK | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/ontology-sdk/overview) |
| 2026-11-19 | L2 本体与动作层 | **Functions on Objects：业务逻辑绑定本体对象，统一计算入口** | Functions on Objects：通过 TypeScript/Python 编写直接操作 Ontology 对象的业务规则与小模型逻辑 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/functions/overview) |
| 2026-11-19 | L3 Agent 编排与评测层 | **Ontology Snapshots：冻结业务时刻做Agent评测** | Ontology Scenarios 与 Snapshots 功能：通过冻结真实业务时刻实现可复现、可评估、可对比的 Agent 性能评测体系 | [X @PalantirTech (官方产品与DevCon动态)](https://x.com/PalantirTech/status/2120251578728812685) |
| 2026-11-18 | L2 本体与动作层 | **Ontology 官方文档：核心概念与数字孪生架构** | Ontology 数字孪生架构：Object/Property/Link/Action 的业务层抽象与数据映射机制 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/ontology/overview) |
| 2026-11-18 | L3 Agent 编排与评测层 | **AIP Logic 块状思维链：把推理拆成可调试积木** | AIP Logic 的块状思维链（Block-based CoT）设计，实现提示词、Ontology 查询、计算函数与结构化输出的无代码编排 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/logic/overview) |
| 2026-11-17 | L5 安全治理与工程落地 | **AIP数据护栏：零留存与防泄漏机制** | AIP 安全架构中的数据护栏设计：输入输出边界、敏感信息防泄漏与零数据留存机制 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/aip/aip-security) |
| 2026-11-17 | L5 安全治理与工程落地 | **高风险决策的人机协同审批链路设计** | AI 伦理治理与合规审计链路：高风险决策中的人机协同审批与可解释性溯源设计 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/aip/ethics-governance) |
| 2026-11-16 | L2 本体与动作层 | **Ontology受控执行机制：AI只申请，平台才执行** |  | [GitHub 深度专题 (palantir-aip-study)](https://github.com/wwwweeia/palantir-aip-study/blob/main/05-ontology-engineering-patterns.md) |
| 2026-11-16 | L5 安全治理与工程落地 | **Markings权限穿透控制LLM上下文** | Markings 细粒度安全标记沿数据血缘穿透控制 LLM 上下文访问权限的实现机制 | [Palantir 官方产品文档](https://www.palantir.com/docs/foundry/aip/control-llm-data-access-with-markings) |

---

## L1 数据接入与管道层 (Data Connection / Pipeline Builder)（已沉淀 1 篇）

### [2026-11-22] Incremental Transforms：增量只读新增行，版本变更强制全量重算
- **原文**：[Dev.to Palantir 技术专栏 — Migrating Legacy ETL to Palantir Foundry: Incremental Transforms, Schema Evolution, and Reconciliation Without Downtime](https://dev.to/kaviwrites/migrating-legacy-etl-to-palantir-foundry-incremental-transforms-schema-evolution-and-18lm)
- **1. 解决什么业务痛点**：常规全量重建随数据总量线性增长且失败会留半写脏数据；Foundry 用事务提交保证原子可见性，用 @incremental 装饰器让 transform 只读上次成功构建后新增的行，逻辑变更时靠 semantic_version 递增强制全量重算。
- **2. 这个功能是怎么工作的**：
  - @incremental(semantic_version=N) 标记 transform → 运行时 Input.dataframe() 只返回上次 commit 后追加的行 → Output 可选 append 或 replace 模式写出；当 semantic_version 递增时系统忽略增量状态，触发全量重算并重置水位线
  - 上游数据集若被 snapshot 整体替换而非 append → 下游 incremental transform 无法识别增量边界 → 系统拒绝增量执行或回退全量；因此 changelog 必须保持 append-only，current-state 表用 Window+row_number 按 order_id 去重取最新行后 replace 写出
- **业务场景实例**：数据工程师在 Code Repositories 提交带 @incremental 的 Python transform → Foundry 调度器按依赖图触发构建 → 只处理新增 changelog 行并将 current-state 结果以事务写入目标 dataset
- **3. 产品设计亮点与取舍**：
  - 取舍差异：放弃了数据库原生 upsert 能力，要求开发者自行用窗口函数建模 latest-state-per-key；换来的是每次构建都有事务级原子性和可回溯的版本链，失败不会污染下游消费
  - 最小实现要素：需定义 changelog 表含业务主键、updated_at、ingested_at 三个排序字段；transform 元数据存 semantic_version 整型与 last_committed_offset；输出表按业务日期分区；校验规则为 cast 后 null_rate 超阈值则 FAIL 阻断提交

## L2 本体与动作层 (Ontology / Object Views / Action Types / Functions)（已沉淀 4 篇）

### [2026-11-23] Ontology单对象：多界面只读同一份房产记录
- **原文**：[Medium Palantir Foundry 专栏 — Building Consumer-Grade Applications on Palantir Foundry: An Ontology-Native Real Estate Product](https://medium.com/@hr_52458/building-consumer-grade-applications-on-palantir-foundry-an-ontology-native-real-estate-product-4f5a48d2ea13?source=rss------palantir_foundry-5)
- **1. 解决什么业务痛点**：常规做法每个界面各存一份房产副本，靠夜间批处理对齐，批处理挂了没人知道，数据静默错乱。这里房产只建一个本体对象，所有界面只读它，系统里没有第二份副本，对齐这一步被删掉。
- **2. 这个功能是怎么工作的**：
  - 每个feed配独立egress策略落成独立dataset，下游富化层按地址做实体解析join，匹配不上的记录不进主对象，最终收敛到界面读取的那一个Property对象。
  - FMV判定入参是该房源每平方英尺价与同ZIP同类中位数，算偏离度输出Overpriced/Underpriced/Fairly Priced四档枚举；同ZIP可比房源不足时直接返回Insufficient Data，不给结论。
- **业务场景实例**：买家在网格点收藏或约看 → Workshop组件调Action写回同一Property对象 → 卖家控制台在同一记录上看到visit请求并approve或decline。
- **3. 产品设计亮点与取舍**：
  - 省掉了数据库、API层和界面间同步代码，代价是放弃各界面自定义数据结构，所有字段必须先在本体里定义好，界面只能读不能另存。
  - 至少定义object_id、address_raw、zip、price_per_sqft、zip_peer_median、comparable_count、fmv_verdict枚举；校验规则：comparable_count低于阈值时verdict强制置为Insufficient Data。

### [2026-11-19] Functions on Objects：业务逻辑绑定本体对象，统一计算入口
- **原文**：[Palantir 官方产品文档 — Ontology 官方文档：Functions on Objects（对象函数与计算模型）](https://www.palantir.com/docs/foundry/functions/overview)
- **1. 解决什么业务痛点**：常规做法把业务规则散落在各应用前端或独立微服务里，同一个对象的计算口径不一致，改一处漏三处。Palantir 把函数签名直接绑定到 Object Type，入参出参都是本体对象，所有消费方调同一份函数，口径天然统一。
- **2. 这个功能是怎么工作的**：
  - 开发者用 TypeScript 或 Python 编写函数，入参声明为具体 Object Type 或 ObjectSet，返回值也必须是 Ontology 类型或基础类型。平台在编译期校验类型签名是否匹配当前 Ontology Schema，不匹配直接报错拒绝发布。
  - 函数发布后自动注册为 Function-backed Action 的后端实现。当 Action 被触发时，平台先执行 Submission Criteria 校验参数合法性，通过后将参数传入函数执行体，函数内部对 Object 的修改由平台统一收集并批量写回 Ontology，函数本身不持有数据库写权限。
  - 函数支持 Batched Execution 模式：入参从单个 Object 扩展为 ObjectSet，平台自动将大批量对象分片传入函数实例并行执行，单次分片大小受 Scale and Property Limits 约束，超限则拆分为多批次顺序提交。
- **业务场景实例**：业务用户在 Workshop 点击「重新计算信用评分」按钮 → 触发 Function-backed Action → 平台调用绑定的 TypeScript 函数读取客户对象及关联订单 → 计算结果写回客户对象的 creditScore 属性。
- **3. 产品设计亮点与取舍**：
  - 取舍差异：放弃了函数自由访问任意数据库的灵活性，换来所有计算逻辑与 Ontology Schema 强绑定——Schema 变更时编译器自动标红所有受影响函数，不会出现运行时才发现字段缺失的事故。
  - 最小实现要素：需定义 function_registry 表含 function_id、input_object_type_ids、output_type、runtime_lang、version 字段；编译期校验入参类型 ID 在当前 Ontology 中存在且属性路径可达；执行层拦截函数对外部存储的直接写操作，只允许通过平台 SDK 返回修改意图。

### [2026-11-18] Ontology 官方文档：核心概念与数字孪生架构
- **原文**：[Palantir 官方产品文档 — Ontology 官方文档：核心概念与数字孪生架构](https://www.palantir.com/docs/foundry/ontology/overview)
- **1. 解决什么业务痛点**：详解 Ontology 如何把底层数据集与流数据映射为业务层的 Object、Property、Link 与 Action。
- **2. 这个功能是怎么工作的**：
  - 详解 Ontology 如何把底层数据集与流数据映射为业务层的 Object、Property、Link 与 Action。
- **业务场景实例**：详见原文完整产品工作流说明。
- **3. 产品设计亮点与取舍**：
  - 建议对照原文梳理我方 AIP 对应模块的产品功能边界。

### [2026-11-16] Ontology受控执行机制：AI只申请，平台才执行
- **原文**：[GitHub 深度专题 (palantir-aip-study) — Palantir Ontology 工程设计模式：对象、关系与 Action Types 建模实践](https://github.com/wwwweeia/palantir-aip-study/blob/main/05-ontology-engineering-patterns.md)
- **1. 解决什么业务痛点**：这就像给 AI 装上‘执行护栏’：它不能直接动系统，只能提申请；真正的操作由平台‘管家’来执行，每一步都留痕、可查、可回滚。对比传统 RAG 只能问答、普通工作流依赖硬编码，这种设计让 AI 真正成为‘可信的业务执行者’。
- **2. 这个功能是怎么工作的**：
  - 『Action Type』：每个 Action 是一个受控写操作模板，需定义输入 Schema、前置条件（如‘工单状态为待分配’）、是否需要人工审批（HITL），以及目标业务系统的调用方式。例如‘分配漏洞工单’Action 必须校验责任人是否存在且有权限，否则拒绝执行。
  - 『执行流水线』：从用户意图出发，经 LLM 解析后调用 Action MCP Tool，平台按五步流程执行：① 输入校验 → ② 前置条件判断 → ③ HITL 审批（如有）→ ④ 写入业务系统 → ⑤ 同步更新图谱并记录审计日志，任何一步失败均回滚图变更。
  - 『语义路由链』：当用户说‘帮我把高危漏洞分给张三’，系统不靠 Prompt 硬塞全量本体，而是先用向量检索找出相关实体（如 Vulnerability、Person）、属性（severity=HIGH）、关系（关联工单），再组装成小范围上下文，引导 LLM 生成合法图查询，避免误操作
- **业务场景实例**：安全运营人员在 Workshop 中输入自然语言：‘上周未分配的高危漏洞有哪些？’系统启动语义路由链，检索命中‘Vulnerability’实体与‘关联工单’关系，生成 Gremlin 查询语句，经 Schema 校验后执行图查询，返回结果并展示在界面。若后续要‘分配’，则触发 Action 流水线，平台校验权限与状态，最终写入工单系统并同步图谱，全程可审计。
- **3. 产品设计亮点与取舍**：
  - 【通用设计精髓与认知校准】常规直觉认为 AI 应直接操作系统，但 Palantir 的真实做法是‘反向写回’：让 AI 只能‘申请’，平台才是‘执行者’。这打破了‘大模型即代理’的幻想，真正实现了‘可控、可审计、可追溯’的可信执行，是 AIP 从‘会答’走向‘能做’的核心跃迁。
  - 【对标框架落位与起步取舍】该能力应沉淀于‘数据本体底座’层，当前起步阶段不必追求全局图谱，优先聚焦一个业务闭环子图（如安全运营），先建好 Object/Link/Action 类型，再对接 Agent 编排运行时。重点抄作业的是：Action 的前置条件+执行流水线+审计日志三件套，而非复杂图结构

## L3 Agent 编排与评测层 (AIP Logic / Agent Studio / AIP Evals)（已沉淀 10 篇）

### [2026-11-25] AIP Evals：用测试集验收 AI 函数再上线
- **原文**：[Palantir 官方产品文档 — AIP 官方文档：核心产品特性目录（AIP Features）](https://www.palantir.com/docs/foundry/aip/aip-features)
- **1. 解决什么业务痛点**：提示词改一版、模型换一个，输出就飘，业务方不敢让 AI 函数直接进生产流程，缺一个能反复跑、能比对的验收手段。
- **2. 这个功能是怎么工作的**：
  - 给每个 AI 函数建一套测试用例集，逐条填输入和期望结果，一键批量跑多轮并换模型对比，系统按评分标准判通过与否，结果汇总成看板供上线决策。
- **业务场景实例**：适合合同要素抽取、工单分类、审批建议这类有明确对错的 AI 函数上线前验收，以及模型供应商切换、提示词大改后的回归检查。
- **3. 产品设计亮点与取舍**：
  - 把评测做成和函数同级的独立资产而非一次性调试面板，用例可沉淀复用；MVP 先做输入输出比对加通过率统计，中间步骤打分和多模型横评可后置。

### [2026-11-24] Agent Stack：会话持久化与类型化上下文驱动多参与者协作
- **原文**：[Palantir 官方产品文档 — AIP 官方文档：Agent Stack 与工具调用体系](https://www.palantir.com/docs/foundry/aip/agent-stack)
- **1. 解决什么业务痛点**：常规做法中Agent每次调用无状态，跨应用或等人审批时上下文丢失需重建。Agent Stack用Session持久保存全部Context Items和Event历史，任何参与者在任意时间点接入同一Session即可恢复完整任务进度。
- **2. 这个功能是怎么工作的**：
  - Session创建时绑定agent_id与初始context_items数组，每个item带type枚举（message/tool_result/recommendation/decision），系统按type决定渲染形态：结构化数据给自动化系统，交互视图给人工决策者
  - Event进入Session后由当前state_machine的event_handler处理：handler读取session_state判断是否满足转移条件，满足则更新context_items并transition到新state（如waiting_for_review），不满足则拒绝或排队
- **业务场景实例**：业务员在Workshop发起采购审批 → Automate检测到金额超阈值时向该Session发送escalation_event → Agent转入等待主管review状态 → 主管在同一Session提交decision类型context_item → Agent恢复执行写回采购单
- **3. 产品设计亮点与取舍**：
  - 取舍差异：放弃了无状态函数调用的简单性，换来跨天跨人跨应用的任务连续性；代价是必须维护Session存储和状态机定义，不能像普通LLM调用那样fire-and-forget
  - 最小实现要素：需建session表（id/agent_id/state/created_at）、context_item表（session_id/type_enum/payload_json/participant_id/timestamp）、event表（session_id/event_type/payload/source_app）；state_machine配置为JSON定义states数组与transitions条件映射

### [2026-11-23] Agentic Runtime：Agent权限按三重身份动态求交
- **原文**：[Medium Palantir AIP 专栏 — Securing Agents in Production (Agentic Runtime, #1)](https://blog.palantir.com/securing-agents-in-production-agentic-runtime-1-5191a0715240?source=rss------palantir_aip-5)
- **1. 解决什么业务痛点**：常规做法给Agent一个固定服务账号权限，导致Agent输出泄露给无权查看该数据的用户。Palantir要求每次执行同时校验owner、service scope、当前委托人三重身份，取交集后才放行，无权用户连执行记录都看不到。
- **2. 这个功能是怎么工作的**：
  - 机制点1：Agent orchestration绑定三个权限源——配置者owner权限、agent service user的OSDK scope、当前on-behalf-of用户的属性标签。运行时对每次Ontology读写请求，系统取三者交集作为有效权限集，缺任一维度则拒绝该次数据访问。
  - 机制点2：当Agent产出结果需通知下游用户时，系统逐条校验接收者的marking和role是否覆盖该结果所涉数据的分类标签。不满足的用户不仅收不到通知，在orchestration界面中也查不到该条执行记录，实现静默隔离而非报错提示。
- **业务场景实例**：销售分析Agent处理含欧洲客户数据的商机时，系统校验每条输出涉及的地理标记，仅向持有欧洲数据marking的用户推送结果并展示执行日志，其余用户完全无感知。
- **3. 产品设计亮点与取舍**：
  - 取舍差异：放弃了给Agent单一高权限服务账号的简便做法，换来每次调用都做三维权限求交的运行时开销，但杜绝了跨权限域数据泄露。
  - 最小实现要素：orchestration表需存owner_id、service_scope_id、delegated_user_id三字段；每次工具调用前查询三方权限集取交集；通知分发前按接收者marking过滤，未通过者不写入可见日志表。

### [2026-11-22] Workflow Lineage：AIP执行链路追踪与生产可观测
- **原文**：[Palantir AIP 官方文档 — AIP 官方文档：AIP 可观测性与生产追踪 (Observability)](https://www.palantir.com/docs/foundry/aip/aip-observability/)
- **1. 解决什么业务痛点**：常规做法下 AIP Logic 调用链跨多个 Function 和 LLM，出错时只能逐段翻日志拼因果。Palantir 把每次执行绑定到 Workflow Lineage 的分布式 trace，按 parent-child span 自动串联，故障定位从人肉拼接变成按 trace_id 一次查全链路。
- **2. 这个功能是怎么工作的**：
  - 执行历史查询：用户输入 workflow_id 或时间范围 → 系统从 Workflow Lineage 索引中检索匹配的 execution record 列表 → 返回每条记录的 status 枚举(success/failure/timeout)、耗时 ms、触发来源(Action/Automate/手动)及关联 trace_id
  - 分布式追踪展开：用户点击某条 execution 的 trace_id → 系统按 span 树结构渲染该次执行涉及的所有子调用(Ontology read、LLM inference、Function invoke、Action write) → 每个 span 标注 start_time/end_time/status/error_message，失败 span 红色高亮并展示入参快照
  - 日志搜索与指标聚合：用户在 log search 界面输入关键词或 object_type 过滤条件 → 系统在结构化日志存储中做全文检索并按 severity 分级返回 → metrics dashboard 按 function_name 维度聚合 p50/p95/p99 延迟与错误率时序曲线
- **业务场景实例**：运维人员发现某 AIP Logic 函数错误率突增 → 进入 Workflow Lineage 按 function_name 过滤 failure 记录 → 展开 trace 定位到具体 LLM 调用 span 超时 → 查看入参确认是 prompt token 超限导致 provider 拒绝
- **3. 产品设计亮点与取舍**：
  - 取舍差异：不在每个 Function 内部手写埋点代码，而是由平台执行引擎在调度层自动注入 span context，业务开发者零改造即获得全链路追踪，代价是无法自定义 span 粒度
  - 最小实现要素：需定义 execution_record 表(execution_id, workflow_id, trigger_source, status, duration_ms, created_at)；span 表(span_id, parent_span_id, execution_id, operation_type, input_snapshot_json, output_snapshot_json, error_code)；采集侧在函数调度入口拦截并写入 span context propagation header

### [2026-11-22] Trace Curation：生产trace入本体转微调训练集
- **原文**：[X @PalantirTech (官方产品与DevCon动态) — @PalantirTech 产品洞察：Own the benchmark. Shape the model. Encode your alpha. At DevCon 7, Palantir Software Engineers...](https://x.com/PalantirTech/status/2121278958683500549)
- **1. 解决什么业务痛点**：常规微调用人工标注或脱敏日志当训练集，样本脱离业务对象，模型学不到企业专有判断。Palantir把生产trace连同Ontology上下文一起落成训练资产，样本自带业务语义。
- **2. 这个功能是怎么工作的**：
  - 采集开关按AIP工作流粒度配置，指定要记录的函数与Agent节点。运行时每次调用写入一条trace，含入参、检索到的Ontology对象引用、模型输出、人工是否采纳。未开启的节点不落记录。
  - 策展环节对trace做筛选与打标，剔除失败调用和未被采纳的输出，保留人工修正后的正确答案作为标签。筛出的集合绑定版本号，交给Model Studio作为微调输入，训练产出的模型再注册回平台供Logic调用。
- **业务场景实例**：业务人员在Workshop里修正Agent建议并提交 → 该次trace被标记为已修正 → 策展时纳入训练集 → Model Studio微调后新模型上线替换原函数。
- **3. 产品设计亮点与取舍**：
  - 省掉了单独建标注平台和人工写样本这一步，训练数据由日常操作副产物直接生成；代价是必须先有稳定的线上流量，冷启动阶段无数据可用。
  - 至少定义trace表：trace_id、workflow_id、node_id、input_payload、context_object_refs、model_output、human_verdict枚举、corrected_output、dataset_version。校验规则：human_verdict为空或调用报错的记录不得进训练集。

### [2026-11-21] AIP Evals：用测试集与裁判模型量化LLM函数输出
- **原文**：[YouTube 模块深挖·AIP Evals评测与权限治理 (LearnWithBeibei) — [视频 · LearnWithBeibei] AIP Evals Tutorial: Test & Score LLM Functions in Palantir](https://www.youtube.com/watch?v=79x-Xf0VZ4Y)
- **1. 解决什么业务痛点**：手动点几条样例无法发现提示词改动引发的回归。AIP Evals 要求绑定固定测试集，每次跑完输出逐条通过/失败表和总通过率，改动前后数字直接对比，回归立刻可见。
- **2. 这个功能是怎么工作的**：
  - 创建 Evaluation Suite 时绑定一个 target function，写入若干 test case，每条包含 input 和 expected condition；选 evaluation function 类型为 LLM-as-a-judge boolean，指定裁判模型（如 Claude Sonnet 5），禁止用被测模型自身做裁判。
  - 运行时系统将每条 test case 的 input 送入 target function 取 actual value，再把 actual value 与该条 condition 一起送入裁判模型；裁判返回 true/false，系统汇总为逐条结果表和 overall pass rate；JSON 解析失败时该条标记 error 而非 pass。
- **业务场景实例**：开发者修改提示词后触发 Eval Suite 运行 → 系统批量调用 target function 并经裁判模型逐条打分 → 写回通过率表与逐条 pass/fail 明细，开发者据此决定是否发布。
- **3. 产品设计亮点与取舍**：
  - 省掉了人工逐条比对的主观判断，但限制了评测只能覆盖预先写好 expected condition 的场景，开放式生成质量仍需人工抽检补充。
  - 最小字段：eval_suite 表含 suite_id、target_function_ref；test_case 表含 case_id、input_payload、expected_condition_text；eval_run 表含 run_id、suite_id、model_version、per_case_result(boolean)、error_flag、overall_pass_rate。校验规则：裁判模型 ID 不得等于 target function 所用模型 ID。

### [2026-11-20] Guideline Evaluation：自动校验医疗必要性并生成申诉信
- **原文**：[Medium Palantir AIP 专栏 — Inside the AIPCon 8 Demos Redefining the Future of Enterprise AI](https://blog.palantir.com/inside-the-aipcon-8-demos-redefining-the-future-of-enterprise-ai-a0a740fe44ce?source=rss------palantir_aip-5)
- **1. 解决什么业务痛点**：常规做法靠人工逐条比对病历与保险公司报销指南，漏诊编码导致拒赔。Palantir 把病历字段、CPT 码、保险规则全部映射进 Ontology 对象，Agent 自动交叉校验后直接输出合规 ICD-10 编码和申诉信草稿，拦截不满足报销条件的诊断项。
- **2. 这个功能是怎么工作的**：
  - 入参为患者 chart 对象（含 CPT 码列表、住院账户 ID、临床记录文本）→ 系统拉取对应 payor 的动态 guideline 规则集 → 逐条匹配临床证据是否满足 medical necessity 阈值，不满足则标记缺失证据字段
  - 当所有必需临床证据字段通过校验时 → Agent 从候选 ICD-10 枚举中选取报销最优编码组合 → 调用文档生成函数拼装 appeal letter 草稿，写回患者账户对象供人工终审
- **业务场景实例**：RCM 专员选中待审病例 → 触发 Guideline Evaluation workflow → 系统读取病历与保险规则、输出合规编码及申诉信草稿 → 写回病例对象等待人工确认提交
- **3. 产品设计亮点与取舍**：
  - 省掉了人工在多个系统间切换查编码、查指南、写信的操作链；限制是保险规则必须预先结构化为可查询对象，不能依赖 PDF 原文模糊匹配
  - 最小要素：patient_chart 表（cpt_codes[]、account_id、clinical_notes）、payor_guideline 表（required_evidence_fields[]、icd10_candidates[]、necessity_threshold）、appeal_draft 表（generated_text、status 枚举 draft/approved/submitted）；校验规则：每条 required_evidence_field 必须在 clinical_notes 中有对应提取结果才放行

### [2026-11-20] Chatbot Studio：检索上下文与工具白名单构建可溯源Agent
- **原文**：[Palantir 官方产品文档 — Agent Studio 官方文档：构建与配置企业级交互式 Agent](https://www.palantir.com/docs/foundry/agent-studio/overview)
- **1. 解决什么业务痛点**：常规做法把全量知识库塞进 prompt 导致幻觉且无法溯源，或让 LLM 自由调用任意 API 导致越权写入。Chatbot Studio 用显式注册的 Context Types 限定检索范围并强制生成 Citation，用 Tools 白名单限定可执行动作集合，未注册的工具直接拦截不传给模型。
- **2. 这个功能是怎么工作的**：
  - Retrieval Context 配置时指定 context_type 枚举（Ontology object set、document media set、custom function），系统按类型走不同检索管道；每条返回片段自动附带 source_rid 和 chunk_offset，前端渲染为可点击 Citation 链接回原始对象或文档段落。
  - Tools 注册面板要求逐条声明 tool_name、description、input_schema（JSON Schema）及绑定的 Action Type RID 或 Function RID；LLM 输出 tool_call 时系统校验函数签名匹配且当前用户对该 Action 有执行权限，校验失败返回结构化错误而非静默跳过。
  - Application State 允许将 Workshop 页面当前选中的 Object RID 列表注入 session 变量，Agent 首轮 prompt 自动拼接这些对象的属性摘要，省去用户手动描述业务实体的步骤。
- **业务场景实例**：运维工程师在 Workshop 设备详情页唤起 Chatbot → 系统自动注入当前设备 Object 属性至 Application State → Agent 检索关联维修工单文档生成带 Citation 的诊断建议 → 用户确认后 Agent 调用注册的 create_work_order Action 写回新工单。
- **3. 产品设计亮点与取舍**：
  - 取舍差异：放弃了让 LLM 自主发现可用工具的灵活性，换取每次 tool_call 都经过签名校验和权限拦截的确定性；放弃了全库 RAG 的召回广度，换取每条回答都能精确引用到具体对象或文档段落的溯源能力。
  - 最小实现要素：需建 agent_config 表含 retrieval_sources（type/source_id/filter_expr）、registered_tools（name/schema/bound_action_id/required_permission）、app_state_bindings（variable_name/object_type_rid）三组字段；检索接口返回必须携带 source_id + offset；tool_call 网关需做 schema validate + permission check 双重拦截。

### [2026-11-19] Ontology Snapshots：冻结业务时刻做Agent评测
- **原文**：[X @PalantirTech (官方产品与DevCon动态) — @PalantirTech 产品洞察：You must own your evals to own your alpha. What makes your organization unique can't be protect...](https://x.com/PalantirTech/status/2120251578728812685)
- **1. 解决什么业务痛点**：常规做法拿公开benchmark或手工编造case测Agent，测不出它在自家业务数据上的真实表现。Palantir把生产环境某一刻的本体状态整体快照下来当测试输入，让每个Agent用自己的真实业务场景做基准，换模型时能直接对比同一份输入下的输出差异。
- **2. 这个功能是怎么工作的**：
  - 创建Snapshot时指定时间戳与对象类型范围，系统将该时刻所有匹配对象的属性值和关联关系序列化为只读副本，后续生产数据变更不影响已冻结副本的内容。
  - 创建Scenario时选择一个已有Snapshot作为基线，用户可在其上修改指定对象的属性值模拟假设条件，系统将修改记录为增量补丁而非覆盖原始快照，评测结束后补丁可丢弃或保留为新版本。
  - 运行Eval时选择目标Agent、绑定一个Snapshot或Scenario作为输入上下文、指定评分函数，系统用该上下文替代生产本体喂给Agent执行，将Agent输出与预期结果逐字段比对后写入评测得分表。
- **业务场景实例**：产品经理发现线上Agent处理某类工单出错 → 从该工单发生时刻创建Snapshot → 修改prompt或切换模型后对同一Snapshot重跑Eval → 对比两次得分决定是否上线新版本。
- **3. 产品设计亮点与取舍**：
  - 省掉了人工构造测试数据集的成本，但限制了评测只能基于已发生过的真实业务状态，无法凭空生成从未出现过的极端边界case，需要额外补充合成数据机制。
  - 至少需要三张表：snapshot_meta（snapshot_id, created_at, object_type_filter, source_timestamp）、snapshot_objects（snapshot_id, object_id, properties_json, links_json）、eval_runs（run_id, snapshot_id, scenario_patch_id, agent_version, model_id, score_json, created_at）。Scenario补丁单独存一张scenario_patches表记录object_id与field-level diff。

### [2026-11-18] AIP Logic 块状思维链：把推理拆成可调试积木
- **原文**：[Palantir 官方产品文档 — AIP Logic 官方文档：无代码编排大模型与本体工具链](https://www.palantir.com/docs/foundry/logic/overview)
- **1. 解决什么业务痛点**：一句话：AIP Logic 是「大模型推理的可视化流水线」，把一次 AI 判断拆成一串有输入输出类型的积木块，无代码拼起来就发布成一个可被调用的函数。普通 Agent 是「给模型一堆工具让它自己想」，过程藏在黑箱里，出错只能看日志猜；普通工作流引擎又完全不懂语义，只能搬数据。Logic 走中间路线：骨架是确定的（查询块取数、函数块算数、条件块分流），只在真正需要判断的那一块交给 LLM，且该块必须交出结构化结果。就像把「一篇作文」改写成「带小标题的填空表格」，每一格都能单独检查、单独重跑。
- **2. 这个功能是怎么工作的**：
  - 『Blocks 块类型与命名变量』：画布上拖拽不同职责的块——LLM 块（选模型、写提示词、挂工具、定输出结构）、Ontology 查询块（按条件搜对象、沿链接取关联对象）、Function 块（调已注册计算函数）、条件/循环块。每块输出是一个命名变量，下游块通过变量选择器引用，如 llm_result.risk_level 直接进条件分支，不用手写 JSON 解析。
  - 『LLM 块的输出 Schema 约束』：LLM 块不是自由吐文本，配置时要声明返回类型：字符串、枚举、结构体、对象数组，甚至直接是 Ontology 对象引用。例如让模型输出 {risk_level: 枚举(高/中/低), reason: 文本, affected_orders: 订单对象列表}，类型不合规即报错，下游块拿到的是强类型数据而非一段待清洗的话。
  - 『本体工具与单步调试面板』：LLM 块可挂 Ontology 查询工具，让模型自己决定搜哪类对象、沿哪条链接展开；调试时右侧面板逐块展示实际输入、工具调用参数与返回、模型输出、耗时与用量，可只重跑某一块并改提示词对比效果，把「思维链」变成可回放的执行轨迹。
  - 『Staged writes 暂存写入』：模型或函数块产生的本体修改先落成暂存编辑集，不直接进本体。界面可预览这批改动的前后差异，交由后续校验块或人工确认后再统一提交，避免一次幻觉直接污染业务对象；这也是评测里能单独「评估本体编辑」的前提。
  - 『发布为 Function 与多入口复用』：编排完成后声明函数输入参数（可含对象类型）与返回类型，发布带版本。同一个 Logic Function 可被 Workshop 按钮点击、Automate 定时/事件触发、Chatbot 当作工具、外部 API 调用，逻辑只写一遍，交互入口和自动化共用同一份可评测资产。
- **业务场景实例**：以供应链延期处置为例：采购员在 Workshop 页面点「评估风险」按钮，或 Automate 每天定时触发同一个 Logic Function。查询块先按条件取出在途订单对象、沿链接拉到供应商与产能对象；LLM 块结合邮件文本与这些对象，调用本体查询工具补查历史交付记录，输出结构化的风险等级、理由与受影响订单列表；函数块算出缺口数量；条件块把高风险分支导向暂存写入，生成待确认的订单调整与预警对象；采购员在界面看差异后确认提交，结果回写本体并通知下游，整条链路的每块输入输出都留痕可复查。
- **3. 产品设计亮点与取舍**：
  - 【通用设计精髓与认知校准】常规直觉是「模型越强、越该放手让它自主规划」；Palantir 反着来：用确定性骨架包住不确定的模型，只在需要判断的块用 LLM，其余交给查询与函数。可观测性不是靠事后日志，而是靠编排结构本身天然分格，这点最该刷新我们的认知。
  - 【对标框架落位与起步取舍】该能力属 Agent 编排运行时，但强依赖本体底座提供对象查询与函数注册。起步别先做自主多轮 Agent，先做「块类型 + 强类型中间变量 + 单块重跑调试」三件套，并把本体查询做成一等公民块，比接十个工具更有价值。

## L4 交互应用与开发层 (Workshop / OSDK / Automate)（已沉淀 3 篇）

### [2026-11-21] Workshop：Object层驱动的人机协同操作应用构建器
- **原文**：[Palantir 官方产品文档 — Workshop 官方文档：构建人机协同的操作应用界面](https://www.palantir.com/docs/foundry/workshop/overview)
- **1. 解决什么业务痛点**：常规做法让前端直接拼SQL取数再硬编码写回接口，导致字段映射散落各处、权限校验绕过本体层。Workshop强制所有读走Object Data Layer、所有写走Action Types，把数据访问收口到统一语义层，杜绝前端越权写入。
- **2. 这个功能是怎么工作的**：
  - Variables系统：定义Object Set Filter Variable绑定某ObjectType的筛选条件，当用户操作Filter List组件时触发变量重算，下游所有引用该变量的Widget自动刷新数据，无需手写联动逻辑。
  - Events机制：Button Group组件配置onClick事件，入参为当前选中Object的主键与Action Type标识；系统先校验当前用户对该Action的执行权限，通过后调用Action写回Ontology，失败则拦截并返回错误提示。
  - Cross-application Commands：App Pairing建立两个Workshop模块间的通信通道，发送端触发Command携带Object引用，接收端订阅该Command后自动定位到对应Object View，实现跨应用的对象级联动而非页面跳转。
- **业务场景实例**：运维人员在Inbox界面选中告警Object → 点击Inline Action按钮触发分派Action → 系统将工单状态写回Ontology并刷新任务列表变量。
- **3. 产品设计亮点与取舍**：
  - 取舍差异：放弃前端自由拼接任意数据源的灵活性，换取读写路径全部经过Ontology层的权限校验与审计一致性，前端开发者不再需要自行实现字段级鉴权。
  - 最小实现要素：需定义variable_registry表存储变量ID、绑定object_type_id、filter_schema_json、recompute_trigger枚举；widget_config表存widget_id、bound_variable_ids数组、event_action_type_id；每次渲染前校验用户对bound object_type的read权限。

### [2026-11-21] Automate：条件持续监测驱动动作与Logic自动执行
- **原文**：[Palantir 官方产品文档 — Automate 官方文档：事件驱动的自动化监测与动作触发](https://www.palantir.com/docs/foundry/automate/overview)
- **1. 解决什么业务痛点**：常规做法把触发条件和执行逻辑写死在同一个定时脚本里，改条件要改代码、改执行也要改代码，且无法按对象粒度精确触发。Automate 把 Condition 和 Effect 拆成独立配置项，条件侧订阅 Ontology 对象集变化或时间表达式，执行侧挂载 Action/Logic/Function，两边独立变更互不影响。
- **2. 这个功能是怎么工作的**：
  - Condition 配置支持三种类型：Time condition 填 cron 表达式按周期触发；Object set condition 绑定一个 Object Set 并设过滤谓词，当集合成员新增或属性值越过阈值时触发；Dataset condition 监听指定数据集更新事件。三者可组合为 AND 逻辑。
  - Effect 配置从四种类型中选取：Action effect 指定 Action Type 及入参映射；Logic effect 指定 AIP Logic Function 并传入触发对象作为上下文；Function effect 调用 Foundry Function；Notification effect 发送平台消息或邮件并可附加 Notepad/Contour 生成的 PDF。每条 Automation 可挂多个 Effect 并配置 Fallback effect 处理主 Effect 失败场景。
  - 执行治理层提供 Evaluation frequency 控制轮询间隔、Manual and automatic retries 配置重试次数与退避策略、Muting/Pausing/Expiration 三个开关分别实现临时静默、暂停调度和到期自动下线，Automation history 记录每次触发的条件快照与 Effect 执行结果供审计回溯。
- **业务场景实例**：运维人员配置 Object set condition 监听高优先级 Alert 对象新增 → Automate 触发 Logic effect 调用 AIP Logic 生成处置建议 → 再触发 Action effect 将建议写回 Alert 对象的 remediation 字段，同时 Notification effect 邮件通知责任人。
- **3. 产品设计亮点与取舍**：
  - 取舍差异：放弃在脚本中自由编写任意触发逻辑的灵活性，换取条件与执行的声明式解耦——非开发人员可在界面上独立修改触发规则或替换下游 Effect，无需碰代码，也无需重新部署。
  - 最小实现要素：需建 automation 表含 condition_type 枚举(time/object_set/dataset)、condition_config JSON(cron 表达式或 object_set_id+filter 谓词)、effect_type 枚举(action/logic/function/notification)、effect_config JSON(目标函数 ID 与入参映射)、execution_identity 字段指定代理执行身份、retry_policy JSON(max_retries/backoff)、status 枚举(active/muted/paused/expired)。另需 automation_execution_log 表记录每次触发的 condition_snapshot 与 effect_result。

### [2026-11-20] OSDK：本体Schema编译为类型安全SDK供外部应用调用
- **原文**：[Palantir 官方产品文档 — Ontology SDK (OSDK) 官方文档：在外部应用中调用本体与动作](https://www.palantir.com/docs/foundry/ontology-sdk/overview)
- **1. 解决什么业务痛点**：常规做法让外部应用直接拼REST请求访问业务数据，字段名拼错或类型不匹配只有运行时才报错，且每个应用各自维护一套鉴权和序列化逻辑。OSDK在编译期把Ontology Schema生成强类型客户端，字段不存在或类型错误直接编译失败，鉴权统一收敛到SDK内置OAuth流程。
- **2. 这个功能是怎么工作的**：
  - 机制点1：开发者在Developer Console注册应用并勾选所需Object Types和Action Types → 平台按勾选范围生成对应语言的SDK包(Java/Python/TypeScript) → SDK内每个Object Type映射为一个带完整属性类型的类，未勾选的类型不出现在SDK中，编译期即不可见
  - 机制点2：TypeScript OSDK提供WebSocket订阅接口，入参为Object Type标识与过滤条件 → 当被订阅对象属性发生变更时平台推送增量事件 → 客户端回调函数接收变更后的对象快照，无需轮询；连接断开后SDK自动重连并从断点续订
  - 机制点3：OSDK调用Action时入参必须匹配Action Type定义的参数Schema → SDK在本地做类型校验，缺必填字段或枚举值越界直接抛编译错误或运行时TypeError → 校验通过后请求发往平台，平台再执行权限检查与业务规则校验，双层拦截
- **业务场景实例**：外部React应用通过TypeScript OSDK查询工单对象列表 → 用户点击审批按钮触发approve Action → SDK将参数序列化并提交平台 → 平台校验权限后写回工单状态字段并通过WebSocket推送变更给所有订阅客户端
- **3. 产品设计亮点与取舍**：
  - 取舍差异：放弃了通用REST API的灵活性，外部应用只能调用注册时勾选的Object Types和Actions，无法绕过Schema约束自由拼查询；换来的是编译期类型安全和统一的鉴权收敛，省掉每个应用自建OAuth和序列化层的重复工作
  - 最小实现要素：需定义应用注册表(app_id, allowed_object_types[], allowed_action_types[])、代码生成器读取Ontology Schema输出强类型客户端、SDK内置OAuth token刷新逻辑、Action调用前本地参数校验器(必填检查+枚举白名单)

## L5 安全治理与工程落地 (Markings 权限 / 架构理念 / FDE 模式)（已沉淀 9 篇）

### [2026-11-26] AIP安全架构：第三方模型零留存与区域端点路由
- **原文**：[Palantir AIP 官方文档 — AIP 官方文档：AIP 安全架构与数据护栏](https://www.palantir.com/docs/foundry/aip/aip-security/)
- **1. 解决什么业务痛点**：企业调用第三方大模型时，提示词和返回结果可能被模型厂商留存或用于训练，造成客户数据外泄风险。
- **2. 这个功能是怎么工作的**：
  - Palantir在接入每个第三方模型前，先与厂商签订技术加合同双重保证：提示词和补全内容即时丢弃不留存、不用于模型再训练、厂商人员无权访问；同时优先选用客户所在区域的模型端点以降低延迟并满足数据驻留要求。
- **业务场景实例**：适用于金融、医疗、政务等对数据出境和隐私合规有硬性要求的行业客户，需要在不牺牲AI能力的前提下消除数据外泄顾虑。
- **3. 产品设计亮点与取舍**：
  - 关键设计亮点是把「零留存」从口头承诺变成了逐厂商的技术验证加合同约束的准入门槛，而非事后审计补救；适用前提是客户愿意接受平台代为托管模型调用链路。

### [2026-11-26] BYOM：自带模型统一接入与权限解耦
- **原文**：[Palantir 官方产品文档 — AIP 官方文档：多模型接入（BYOM）与模型路由管理](https://www.palantir.com/docs/foundry/aip/bring-your-own-model)
- **1. 解决什么业务痛点**：客户因合规或自有微调模型需接入平台时，缺乏与内置模型同等的限流、权限和可观测治理能力。
- **2. 这个功能是怎么工作的**：
  - 管理员通过 REST API 或自托管计算模块注册模型后，底层数据源权限即与终端用户解耦，访问仅由 Control Panel 的启用开关控制，同时继承三级限流体系（租户→项目默认70%→用户）。
- **3. 产品设计亮点与取舍**：
  - 注册即切断源权限的设计让模型分发不再依赖底层连接授权，配合租户-项目-用户三级限流实现自带模型与内置模型完全一致的治理体验。

### [2026-11-26] FDE模式：驻场判断力如何沉淀为产品资产
- **原文**：[GitHub 深度专题 (palantir-aip-study) — Palantir FDE（前线部署工程师）模式与产品演进机制解析](https://github.com/wwwweeia/palantir-aip-study/blob/main/02-fde-forward-deployed-engineer.md)
- **1. 解决什么业务痛点**：企业AI项目失败多因技术团队不懂业务、业务团队不懂翻译需求，中间缺一个能同时做技术判断和业务判断的人把系统真正跑起来。
- **2. 这个功能是怎么工作的**：
  - FDE常驻客户现场，在需求讨论中当场判断哪些该建模为Ontology对象，再把反复出现的共性问题抽象为可复用模式，逐步固化为Workshop模板和OSDK脚手架，让后续客户自助完成标准部署。
- **3. 产品设计亮点与取舍**：
  - FDE的核心价值不是完成交付而是把判断力编码进工具；如果所有工作只停留在交付层面没有沉淀为可复用资产，就是在消耗商业模式而非强化它。

### [2026-11-25] 三档路径决策：按场景复杂度选AI落地深度
- **原文**：[GitHub 深度专题 (palantir-aip-study) — 国产 AI 平台借鉴 Palantir AIP 的产品设计与落地行动指南](https://github.com/wwwweeia/palantir-aip-study/blob/main/04-action-guide-domestic-ai.md)
- **1. 解决什么业务痛点**：团队常犯的错误是不管场景简单还是复杂都上全套语义建模加权限治理，结果要么过度建设没人用，要么治理欠债上线后出事。
- **2. 这个功能是怎么工作的**：
  - 按数据复杂度、场景需求、组织成熟度三个维度打分，低档只做检索问答加工作流，中档加一层业务对象关系定义和跨系统操作封装，高档才做完整语义建模加治理平台化。
- **业务场景实例**：适用于我们自研 AIP 产品的客户分级交付策略设计：面对不同成熟度的客户，产品应该提供哪些功能档位、默认开启哪些模块、何时引导客户升级。也适用于内部立项时判断某个 AI 场景该投入多少建模和治理工程量。
- **3. 产品设计亮点与取舍**：
  - Palantir 的溢价不在单个功能而在三层一体化的集成工程量；我们 MVP 应先做最轻档跑通场景再按需叠加语义层和治理层，切忌一上来就建平台。

### [2026-11-24] Object Permissioning：Schema与数据双层权限隔离
- **原文**：[Palantir 官方产品文档 — Ontology 官方文档：Object Permissioning（对象与属性级权限控制）](https://www.palantir.com/docs/foundry/object-permissioning/overview)
- **1. 解决什么业务痛点**：常规做法把schema定义和数据值混在同一权限体系里，导致用户要么看到全部字段要么完全看不到类型。Palantir把ontology资源（类型/属性名/链接定义）和objects/links（实际主键值与属性值）拆成两层独立授权，schema可见不等于数据可读。
- **2. 这个功能是怎么工作的**：
  - Ontology资源层：对object type、link type、action type分别配置角色权限 → 用户能看到类型定义和属性schema但无法查询任何实例数据 → 需额外授予object级读权限才能拿到实际值
  - Objects and links层：按对象实例粒度绑定安全策略（Object Security Policies）→ 查询时系统逐条校验当前用户对该primary key的读权限 → 不满足条件的对象直接从结果集中剔除，不报错只静默过滤
- **业务场景实例**：业务员在Object Explorer搜索飞机对象 → 系统先校验其对Airplane object type的资源权限 → 再逐条过滤其无权查看的具体飞机实例 → 返回仅含授权对象的列表
- **3. 产品设计亮点与取舍**：
  - 取舍差异：省掉了在每个应用层重复写数据过滤逻辑的工作量，但要求所有查询必须经过统一权限拦截层，不允许绕过直连底层存储
  - 最小实现要素：需在元数据表增加resource_acl字段存角色列表，在对象表增加security_policy_id外键关联策略表，策略表定义user/group到object粒度的allow/deny规则，查询接口统一注入WHERE子句做行级过滤

### [2026-11-24] 案件工作流：Agent串联多步骤消除人工交接
- **原文**：[YouTube 模块深挖·AIPCon客户真机Demo (Palantir) — [视频 · Palantir] Redefining Wealth Management | Citi Wealth at AIPCon 7](https://www.youtube.com/watch?v=IZRCw5WnJm8)
- **1. 解决什么业务痛点**：常规做法中一个财富管理案件需经多个团队串行处理，每次交接产生等待和信息丢失。Palantir把各步骤封装为Agent可调用的Action链，一次触发跑完全链路，交接次数减少80%，单案耗时从9天降到秒级。
- **2. 这个功能是怎么工作的**：
  - 案件入参包含客户ID、产品类型、合规检查项枚举列表。Agent按预定义DAG顺序依次调用数据查询Function和写回Action，每步校验前置步骤输出状态为completed才放行下一步，否则挂起并报错给运营人员。
  - 每个Action节点绑定Ontology对象类型与属性写回范围，Agent只能写入该节点声明的字段集合。当某节点执行失败时系统记录失败节点ID与错误码，支持从该节点重试而非整条链路重跑。
- **业务场景实例**：客户经理提交新案件 → Agent按DAG依次调用合规校验、产品匹配、定价计算等Action → 各步骤结果写回案件Ontology对象属性，最终状态标记为已完成。
- **3. 产品设计亮点与取舍**：
  - 省掉了人工在多个系统间复制粘贴和排队等待的环节，但限制了每个节点只能操作声明范围内的字段，不允许Agent跨节点自由读写。
  - 最小实现需要：案件表含case_id、status、current_step_id字段；步骤定义表含step_id、action_type、allowed_fields、depends_on_step_id；每步执行前校验depends_on步骤status=completed。

### [2026-11-17] AIP数据护栏：零留存与防泄漏机制
- **原文**：[Palantir 官方产品文档 — AIP 官方文档：AIP 安全架构与数据护栏](https://www.palantir.com/docs/foundry/aip/aip-security)
- **1. 解决什么业务痛点**：这就像一个‘数据防火墙+自焚装置’——所有进入大模型的请求，都像快递包裹一样被严格安检后送入，但一旦完成任务，包裹连同快递单就立刻在原地销毁，不留任何副本或日志。它解决的是客户最担心的‘我输入的数据会不会被偷偷存下来’这一根本性信任问题。
- **2. 这个功能是怎么工作的**：
  - 『零数据留存机制』：当用户通过 AIP 提交一个包含敏感信息的查询（如客户身份证号+交易记录），系统会在发送至第三方模型前进行加密封装，并在模型返回结果后立即清除所有临时缓存与传输日志。即使模型服务端出现故障或被攻击，也无法获取原始数据。
  - 『输入输出边界隔离』：所有输入（prompt）和输出（completion）均在 AIP 内部构建为独立的、生命周期极短的内存通道，不写入任何磁盘或数据库。例如，一次生成报告的流程中，原始数据仅存在于短暂的内存堆栈中，完成后即被垃圾回收，无法通过调试或日志回溯复现。
  - 『技术+合同双保险』：Palantir 不仅在技术上实现数据即时丢弃，还要求第三方服务商签署法律协议，明确禁止其存储、分析或使用客户数据。若违反，将触发违约赔偿条款，形成‘技术断电 + 法律追责’双重威慑。
- **业务场景实例**：某银行风控人员在 AIP 工作台输入：‘分析客户张三最近三个月的交易行为是否存在洗钱风险’，其中包含姓名、账户号等敏感字段。系统自动识别并注入安全护栏：数据经加密封装后传给 Azure OpenAI，模型返回摘要后，整个对话上下文立即从内存中清除。最终只保留结构化结论（如‘高风险’标签）供人工审核，原始数据从未落地，也未被任何第三方留存。
- **3. 产品设计亮点与取舍**：
  - 【通用设计精髓与认知校准】常规认知认为‘只要权限控制好就行’，但 Palantir 的真实做法是：**即使权限开放，也要保证数据不能留存**。这打破了‘可用即等于可存’的直觉陷阱，提醒我们：真正的数据安全不是‘管住人’，而是‘让数据无处可留’，这是对隐私保护的极致升级。
  - 【对标框架落位与起步取舍】该能力应沉淀于 L5 安全治理层，当前起步阶段不必追求全链路自研，但必须在 Agent 编排运行时（L3）与部署底座（L4）之间建立‘数据不留存’的强制契约。建议优先在 API 网关层引入‘一次性输入-即时销毁’模式，直接抄作业：所有对外调用必须配置‘无持久化’开关。

### [2026-11-17] 高风险决策的人机协同审批链路设计
- **原文**：[Palantir 官方产品文档 — AIP 官方文档：AI 伦理治理与合规审计链路](https://www.palantir.com/docs/foundry/aip/ethics-governance)
- **1. 解决什么业务痛点**：这个机制就像 AI 系统的‘手术室麻醉师签字流程’——不是简单地让模型跑完就出结果，而是当系统判断某次输出涉及重大影响（如裁员建议、贷款拒批）时，自动暂停并要求人类专家介入审批。它把‘AI 做决定’变成‘人+AI 共同做决定’，让每一步关键判断都有迹可循、有人负责。
- **2. 这个功能是怎么工作的**：
  - 『High-Risk Decision Triggers』：当模型输出命中预设规则（如涉及敏感人群、金额超阈值、结论为‘拒绝’等），系统自动标记为高风险，并在 UI 中以红色警示条显示，同时触发审批工作流，强制跳转至审批界面。
  - 『Human-in-the-Loop Approval Workflow』：审批流程支持多角色串行或并行审批，每个审批节点需填写理由、上传依据文件，并可附带修改建议；审批通过后，系统自动生成包含原始输入、模型推理路径、审批记录的完整审计快照。
  - 『Audit Trail for Ethical Decisions』：所有高风险决策的审批过程被永久记录在审计日志中，包括谁审的、何时审的、意见内容、是否采纳，且与数据血缘和模型版本绑定，支持按时间、用户、事件类型进行精准回溯查询。
- **业务场景实例**：一名银行风控人员在使用 AIP 处理贷款申请时，系统生成一份‘建议拒贷’的报告。由于该决策涉及个人信用且金额超过 50 万，系统自动识别为高风险，弹出审批窗口。审批人看到完整的模型推理摘要、申请人画像及历史行为数据，可在界面上勾选‘同意’‘驳回’或‘退回修改’，并填写审批理由。一旦提交，系统立即生成带有时间戳和签名的审计记录，并将最终决策写入业务数据库，同时通知相关监管方备案。
- **3. 产品设计亮点与取舍**：
  - 【通用设计精髓与认知校准】Palantir 的核心洞察是：真正的伦理治理不是靠‘禁止’或‘提示’，而是通过‘强制流程化’把责任嵌入系统。常规直觉认为只要加个‘警告框’就够了，但 Palantir 用的是‘不可跳过的工作流’，让人为干预成为系统默认路径，这才是防止‘AI 背锅’的根本。
  - 【对标框架落位与起步取舍】该能力应沉淀于 L5 治理层，当前起步阶段不必追求全链路自动化，但必须在 Agent 编排运行时（L3）中预留‘高风险判定钩子’接口，优先借鉴其‘触发-审批-留痕’三段式设计，作为后续构建可信 AI 闭环的基础模块。

### [2026-11-16] Markings权限穿透控制LLM上下文
- **原文**：[Palantir 官方产品文档 — AIP 官方文档：通过 Markings 控制大模型数据访问权限](https://www.palantir.com/docs/foundry/aip/control-llm-data-access-with-markings)
- **1. 解决什么业务痛点**：这就像给每个进入大模型的‘对话内容’贴上一张‘保密等级标签’，系统不仅看内容本身有没有敏感词，更要看使用者的‘身份通行证’是否允许访问这些标签。传统 RAG 只管‘查什么’，Palantir 则连‘谁有资格问’都管得死死的。
- **2. 这个功能是怎么工作的**：
  - 『Token级标记校验机制』：每当用户发起 AIP 请求，系统会读取当前 Foundry 会话令牌（token）中携带的所有强制性 Markings（如 A、B、C），并将其与策略配置的允许列表逐项比对。只要令牌中出现一个不在白名单中的标记，哪怕实际查询的数据没有这个标记，请求也会被直接拒绝。
  - 『非数据依赖型权限判断』：该机制不依赖于请求中具体数据是否带有特定 Markings，而是基于用户会话的权限上下文做判断。例如，一个用户虽然只查了无敏感标记的数据，但其会话令牌包含了未授权的 C 标记，依然会被拦截，防止‘越权访问’的隐性风险。
  - 『双层策略覆盖机制』：存在全局策略（Enrollment Policy）和模型级策略（Registered Model Override）两层控制。全局策略默认适用于所有模型；而注册模型可自定义更严格的策略，甚至完全绕过全局限制，实现‘按需隔离’的灵活管控。
- **业务场景实例**：某政府机构分析师在 Foundry 中打开一个含‘机密-国防’标记的项目，其会话令牌自动带上该标记。当他通过 AIP 提问‘分析近期边境部署趋势’时，系统发现其令牌含有未被允许的‘机密-国防’标记，即使问题本身未引用敏感数据，AIP 仍会拒绝响应。此时系统返回错误提示：‘当前会话权限不允许调用 AIP 模型’，有效防止了潜在数据泄露。
- **3. 产品设计亮点与取舍**：
  - 【通用设计精髓与认知校准】常规认知认为权限控制只需看‘数据有没有标记’，但 Palantir 的设计揭示：真正的安全在于‘人+数据’的联合风险评估——即用户的会话权限才是决定能否触达模型的关键。这打破了‘数据可见性=访问权’的直觉误区，提醒我们：权限必须前置到请求源头，而非事后审查。
  - 【对标框架落位与起步取舍】该能力应沉淀在 L5 安全治理层，属于最底层的防护基座。当前起步阶段，不必追求复杂策略体系，但必须在 Agent 编排运行时入口处植入类似‘请求令牌标记校验’的拦截逻辑，优先保障‘谁可以问’的边界清晰，这是 AIP 安全的起点。
