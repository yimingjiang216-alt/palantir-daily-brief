# Palantir AIP 产品深度洞察

面向规划自研 AIP 的产品团队：每个工作日 09:00，从全网深度专栏、推特（X）核心账号、技术社区与 Palantir 官方文档中筛选 **1~2 篇高颗粒度的产品机制拆解**，由千问提炼出「核心产品机制 + 业务场景工作流还原 + 自研 AIP 启示」推送至飞书群。

---

## 为什么和「科技前沿简报 (`report`)」逻辑完全不同？

| 维度 | 科技前沿简报 (`report`) | 本项目 (`palantir-daily-brief`) |
| :--- | :--- | :--- |
| **底层模型** | **增量新闻流**：卡死 3 天时间窗口，当天 PK 选 5 条，其余作废 | **存量知识池 + 慢增量（`pool.json`）**：好文章跨年不过期，入池排队每日消费 |
| **筛选标准** | 新闻重磅度（融资、发布、政策） | **产品拆解颗粒度**（Ontology 四要素、AIP Logic 7 步生命周期、权限 Markings、Agent 自主权旋钮、端到端工作流） |
| **噪音剔除** | 剔除公关软文与跨赛道新闻 | **一票否决纯股价/财报估值（Rule of 40、165% 续费率炒作）、高管政治选举口水、招聘贴** |
| **单篇处理** | 基于摘要生成一句话快讯 | **拉取最高 1.2 万字全文**，按《Palantir AIP 产品深度解读》样板拆出四层结构 |

---

## 全链路架构（3 阶段）

```
[1. 五路深度源抓取 (src/fetch.py)]
   ├─ 中文深度专题：GitHub palantir-aip-study 全文 + 中文架构搜索
   ├─ 推特 (X) 核心解读：@PalantirTech / @chadwahl / @PalantirVision (经 Jina 渲染)
   ├─ 英文技术社区：Dev.to #palantir / Medium #palantir / HackerNews Algolia (OAG/Ontology)
   ├─ 官方工程博客：blog.palantir.com/feed
   └─ 官方核心文档：/docs/foundry/aip/* 12 个核心架构与安全治理模块
          ↓ 代码级硬过滤 (is_noise 踢掉股票、政治、招聘)
[2. 千问深度评分入池 (src/brief.py -> pool.json)]
   ├─ 已在 pool.json 里的 URL 直接跳过（零重复打分、零重复发送）
   ├─ 新增候选由千问 (qwen-flash) 按产品机制颗粒度打 0~10 分
   └─ >= 7 分标为 unread 入池排队；< 7 分标为 rejected 永久淘汰
          ↓
[3. 每日出队全文精读 + 飞书推送 (src/notify.py)]
   ├─ 从 pool.json 取出分数最高的 1~2 篇 unread 文章
   ├─ 拉取完整正文（GitHub Raw / Jina Reader / HTML 正文提取，最高 12,000 字）
   ├─ 千问按样板结构拆解：① 核心产品机制 ② 业务场景工作流还原 ③ 自研 AIP 启示 ④ 原文链接
   └─ 推送飞书成功 → 标记 status="sent" 并回写 pool.json（未配 webhook 时仅预览，不消耗未读储备）
```

---

## 环境变量与 GitHub Secrets

| 变量名 | 当前状态 | 说明 |
| :--- | :--- | :--- |
| `LLM_API_KEY` | ✅ 已配置 | 阿里云百炼 API Key |
| `LLM_BASE_URL` | ✅ 已配置 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | ✅ 已配置 | `qwen-flash` |
| `FEISHU_WEBHOOK` | ⏸️ 留空待填 | 目标飞书群自定义机器人 Webhook（留空时仅更新知识池并打印日志预览） |
| `FEISHU_SECRET` | ⏸️ 可选 | 若飞书机器人开启签名校验则填写 |

---

## 本地运行

```bash
pip install -r requirements.txt
python src/notify.py
```
