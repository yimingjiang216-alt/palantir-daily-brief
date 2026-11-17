# 对标 Palantir Action Type 的受控写操作功能设计

> **文档状态**：`⏳ AI 初稿 · 待产品经理审阅`（In-the-Loop 环节）
> **架构层级**：L2 本体与动作层
> **参考来源**：https://www.palantir.com/docs/foundry/action-types/overview
> **生成日期**：2026-11-17
> **生成模型**：qwen3.5-122b-a10b

---

## 一、业务背景与痛点

当前 AIP-FDS 本体层缺乏统一写入口，前端直连数据库导致权限校验绕过、审计缺失及业务逻辑分散。参考 Palantir Ontology 架构，需构建 Action Type 作为唯一写操作载体。本功能旨在确保所有数据变更经预定义动作执行，实现权限粒度控制与操作留痕。在 MVP 阶段，通过标准化写接口，解决多系统间数据一致性难保障问题，为上层 Agent 编排提供可信数据修改能力，奠定安全治理基础。

## 二、目标与非目标

### 2.1 目标

- 100% 本体对象写操作经由 Action Type 拦截
- 支持 Simple Action 与 Function-backed Action 两类执行模式
- 建立完整的动作提交审计日志链

### 2.2 本轮非目标

- 暂不支持多级审批工作流
- 暂不支持跨事务的复杂分布式锁机制

## 三、用户故事

- **作为 产品经理**：作为产品经理，我希望配置 Action Type 的参数 Schema 与权限组，以便灵活定义业务规则
- **作为 研发工程师**：作为后端开发，我希望 Action 请求自动校验参数类型与必填项，以减少重复代码
- **作为 运营人员**：作为运营，我希望查看动作执行结果与失败原因，以便快速排查数据异常

## 四、核心对象与数据模型

| 对象 | 关键字段 | 说明 |
| :--- | :--- | :--- |
| `ActionType` | id: string, name: string, object_type_id: string, mode: enum(simple/function) | 动作定义元数据 |
| `ParameterSchema` | api_name: string, type: enum(string/int/bool), required: bool, default_value: any | 输入参数结构 |
| `WritePermission` | group_ids: list[string], role_ids: list[string] | 可提交角色或群组 |

## 五、交互流程

1. 步骤 1：用户在 Workshop 界面点击「提交变更」按钮，弹出 Action 配置模态框
2. 步骤 2：用户填写表单参数，前端实时校验必填项，点击确认后发送 Action 请求
3. 步骤 3：系统返回执行状态（成功/失败），并在右侧面板刷新对象最新属性值

## 六、验收标准

- [ ] Given 用户无 WritePermission 权限 When 提交 Action Type 请求 Then 系统返回 403 错误并记录拒绝日志
- [ ] Given 参数 Schema 中某字段设为必填 When 用户未填写该字段 Then 前端阻止提交并高亮显示错误提示
- [ ] Given 用户拥有权限且参数合法 When 提交 Simple Action 请求 Then 系统更新本体属性并生成一条审计记录

## 七、MVP 范围与取舍

本轮仅支持单对象属性更新的 Simple Action 及调用自定义函数的 Function-backed Action。不包含审批流、批量操作及冲突检测。重点打通 FDS 本体到动作层的鉴权链路，确保写操作不直连 DB，验证审计日志完整性，为后续 Agent 交互预留标准接口。

## 八、风险与应对

- 函数执行超时可能导致 Action 阻塞，需设置熔断机制
- 权限模型若与现有 IAM 不一致，可能引发访问控制漏洞

## 九、待确认问题

- [ ] Function-backed Action 的上下文变量如何注入？
- [ ] 审计日志存储周期与归档策略由哪个团队负责？

---

## 附录：Palantir 原始参考规格

**产品设计规格**：需定义：① Action Type 名称与所属 Object Type；② 输入参数 Schema（每个参数的 API 名称、类型、是否必填、默认值）；③ 执行权限（哪些角色/Groups 可提交）；④ 写回逻辑（直接更新本体属性 / 触发 Function 做复杂计算）；⑤ 提交后是否需要审批或二次确认。

**自研对标参考**：自研 AIP-FDS 数据与本体底座需内置动作层能力：所有对本体对象的写操作必须通过预定义 Action Type，禁止前端直写数据库。这样在权限粒度、审计留痕、逻辑复用上都有保障。起步阶段可先支持「Simple Action」（单对象属性更新）与「Function-backed Action」（调用自定义函数）两类。

**规格详情**：Action Type 是 Palantir Ontology 中受控写操作的载体。前端 Workshop 或 OSDK 应用不能直接修改对象属性，必须提交一个 Action Type 请求。系统会校验提交者权限、参数合法性、对象状态约束，通过后执行写回。
