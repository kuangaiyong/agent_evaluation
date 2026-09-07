# 智能体评测平台原型重做（SaaS 风格高保真）

## 分诊

**feature** —— 外部可观察行为改变：模块结构、品牌命名、视觉体系、交互路径全部替换，不是等价重构。

## 我读到的需求

| # | 需求 | 来源 |
|---|---|---|
| 1 | 重新设计一份**高保真 HTML 原型**，对象是我们部门自用的智能体评测平台 | [描述] |
| 2 | 用 `ui-ux-pro-max` skill 做设计决策（配色、字体配对、组件规范） | [描述] |
| 3 | 用户规模约 **1000 人** | [描述] |
| 4 | **不依赖阿里云的能力与产品**（SLS / 云监控 2.0 / MSE / ARMS / LoongSuite 等一律不出现） | [描述] |
| 5 | SaaS 风格，参考 `ui-ux-pro-max-skill.nextlevelbuilder.io/demo/customer-support-crm` | [描述] |
| 6 | 「数据中心」改名为 **数据魔方** | [描述] |
| 7 | 「AgentLoop」字样改为 **TAgenEval** | [描述] |
| 8 | 要有**真实交互**：页面跳转、按钮点击跳转等，不是静态图 | [描述] |
| 9 | 信息架构与功能清单参考 `产品调研/AgentLoop/` 的调研成果（12 模块 / 26 子页 / 21 内置评估器 / 4 类数据来源等） | [我的推断] |
| 10 | 参考页实为**营销落地页**（Hero + CTA + 定价导航），不是控制台界面；用户要的应是其**视觉调性**而非页面类型 | [我的推断] |

### 已勘定的基线事实（自查，不占用 G1）

- 现有原型 `docs/prototype.html` 共 **15 屏**（access / audit / badcases / budget / dashboard / datacenter / evaluators / metrics / notifications / onboard / regression / system / tasks / trace / traces），2908 行，纯手写 HTML+CSS+JS，无框架，仅引 Google Fonts
- 配套 `docs/prototype.smoke.js` 有 **28 项 jsdom 断言**（导航切屏、弹窗、行下钻、筛选、排序）
- 项目 CLAUDE.md 明确：**`docs/prototype.html` 是界面的事实来源**，改界面的顺序是「先改原型、再改代码」
- 打分公式与锁定数字（α=0.8 / β=0.2 / τ=0.75 / k=3，关键链路 5；结果须同时报 Average / pass@k / pass^k）权威源在外层 `00-总纲` 与 `01-指标字典`，**原型只能消费不能改**
- 指标字典 md 基线 92 条（12 组），HTML 增订版 97 条
- 参考页视觉调性实测：靛紫主色（`--color-primary`）+ 次色渐变、**DM Sans** 字体、大圆角（`rounded-xl`）、极浅紫灰底、白卡片轻阴影、胶囊徽章、状态色 橙(Open)/青(Pending)/绿(Resolved)、留白疏朗、带 `dark` class

## 待澄清（G1）

| # | 问题 | 不同答案导致的不同结果 |
|---|---|---|
| 1 | **模块骨架取谁**：照搬 AgentLoop 12 模块（剔除阿里云特有）／以现有 15 屏为基础增补／重新做信息架构 | 决定原型有哪些屏、导航怎么分组。选错会做出一套和部门既有方法论对不上的界面 |
| 2 | **与现有 `docs/prototype.html` 的关系**：新增独立文件并存／直接替换 | 替换会让 28 项 smoke 断言全部失效，且已实现的 phase1 后端界面口径与新原型不一致，需连带返工；并存则短期有两份「事实来源」，需明确谁优先 |
| 3 | **参考页的用法**：只取视觉调性做控制台／另外再做一个营销落地页 | 决定是否要多做 Hero、定价、注册引导等一整套对外页面 |
| 4 | **1000 人规模体现在哪**：需要多团队/项目空间隔离（类似 AgentSpace）＋角色权限＋配额／单一工作区只做角色权限 | 决定导航是否有空间切换器、是否需要成员管理与配额界面 |

## 非目标

- **不实现后端**：本次只产出 HTML 原型，不动 `backend/`、`frontend/` 的真实代码
- **不改方法论数字**：打分公式、α/β/τ、试次 k、指标条目数一律沿用外层文档，原型里出现的数字必须与之一致
- **不引入阿里云任何产品概念**：SLS / 云监控 / MSE / ARMS / LoongSuite / AgentSpace 等命名与依赖全部不出现
- **不做真实数据对接**：原型内数据为演示用静态数据

## 冻结后的口径

G1 于 2026-09-06 答毕，以下为后续所有工序的唯一依据。

### 「不依赖阿里云」的边界（用户 2026-09-06 补充裁定）

用户明确：**LoongSuite 需要引入，后续作为智能体无侵入接入的技术栈。** 据此把「不用阿里云」的边界重划为「**不依赖需要云账号与付费的商业服务**」，而非「不出现任何阿里系名字」：

| 保留 | 理由 |
|---|---|
| **LoongSuite**（Python Agent / Pilot / eBPF 探针） | Apache 开源、可自部署、无云账号依赖；**是我们选定的无侵入接入技术栈**；phase1 已实现的接入中心本就是 LoongSuite 三通道口径 |
| **OpenTelemetry / OTLP 协议** | 开放标准 |
| 被观测方的框架名（LangChain/LangGraph、AgentScope、Dify、Claude Code、Codex 等） | 它们是**被接入对象**不是我们的依赖；接入中心不列这些就失去意义 |

| 剔除 | 替代 |
|---|---|
| SLS 日志服务 | 自建存储，原型不暴露存储实现 |
| 云监控 2.0 / CMS 工作空间 | 自建仪表盘与告警 |
| MSE AI 治理中心 | 自建 Agent 资产托管 |
| ARMS（含 ARMS 探针命名、LicenseKey、workspace 概念） | 自建 OTLP 采集网关 + 接入 Token |
| AgentSpace | 工作空间 / 项目 |
| AI 积分计费 | 自定义配额单位（评测次数 / Token 用量） |

**上报链路口径**：探针（LoongSuite）→ **自建 OTLP 采集网关** → 自建存储。原型的接入指引里展示的 endpoint 为内网自建网关，不出现任何 `*.aliyuncs.com` 域名。

### 评估能力来源改为 DeepEval（用户 2026-09-06 补充裁定）

用户明确：**92 条指标字典不再需要，后续通过开源库 DeepEval 预置平台的评估器。**

**平台侧变更**：删除「指标字典」屏；评估器模块承接其职能，改为「**DeepEval 预置评估器 + 自定义评估器**」两类。

已核实的 DeepEval 内置评估器（经 Context7 查 `/confident-ai/deepeval` 官方文档，非凭印象）：

| 分组 | 评估器类名 |
|---|---|
| RAG（单轮） | `AnswerRelevancyMetric` · `FaithfulnessMetric` · `ContextualRelevancyMetric` · `ContextualPrecisionMetric` · `ContextualRecallMetric` |
| Agentic | `TaskCompletionMetric` · `ToolCorrectnessMetric` · `ArgumentCorrectnessMetric`（官方 README 另列 goal accuracy / step efficiency / plan adherence） |
| 多轮会话 | `TurnRelevancyMetric`（带 `window_size` 滑窗） · `RoleAdherenceMetric`（需 `chatbot_role`） · `KnowledgeRetentionMetric` · `ConversationCompletenessMetric` |
| 安全与质量 | `HallucinationMetric` · `BiasMetric` · `ToxicityMetric` · `SummarizationMetric` |
| 自定义 | `GEval`（自然语言 criteria + `evaluation_params`） · `DAGMetric` / `ConversationalDAGMetric`（决策树式确定性评分） |

评估器通用参数（作为原型「创建/编辑评估器」表单的字段依据）：`threshold`（DeepEval 默认 0.5，**我们取 τ=0.75**）、`model`、`include_reason`、`strict_mode`（二元 1/0）、`async_mode`、`verbose_mode`、`flaky`。

**保留不变**：打分公式 `task_score = s_safety × (α·s_completion + β·s_robustness)`、α=0.8 / β=0.2 / τ=0.75 / k=3（关键链路 5）、Average / pass@k / pass^k 三口径 —— 这些是聚合层与判定层的口径，与「评估器由谁提供」无关，用户本次未推翻。三个分量与 DeepEval 评估器的映射关系属设计工作，在 G2 提出并标为待确认。

**连带影响（需用户后续决定，本次不处理）**：

- phase1 已实现的 `metric-dictionary` 能力域与 `/metrics` 页面将失去依据
- `backend/scripts/sync_metrics.py`（从外层 `01-指标字典` 分册解析 92 条并单向同步）将失效
- 项目 CLAUDE.md 的架构主线「指标字典是单向同步的只读实体」需改写
- **外层方法论文档的 92 条指标（12 组）不受本次影响，仍是方法论资产**；但它与平台就此脱钩 —— 文档继续维护、还是同步改为 DeepEval 口径，请你后续定夺

### 用户裁定（4 项）

| # | 口径 | 用户选择 |
|---|---|---|
| 1 | **模块骨架**：以 AgentLoop 12 模块分组为骨架，剔除阿里云特有部分，并补入我们自己的方法论资产（指标字典 92 条、Bad Case 库、回归门禁） | 选项 A |
| 2 | **新旧关系**：**直接替换 `docs/prototype.html`**，只留一份事实来源 | 选项 B（非推荐项，代价已告知并确认） |
| 3 | **参考页用法**：只取视觉调性（靛紫主色 / DM Sans / 大圆角 / 白卡片轻阴影 / 疏朗留白 / 胶囊徽章），做控制台应用界面，不做营销落地页 | 选项 A |
| 4 | **规模形态**：多团队空间 + 角色权限 + 配额；顶部有空间切换器，资源按空间隔离，含成员管理与用量配额 | 选项 A |

### 口径 2 的连带影响（已确认接受）

- `docs/prototype.smoke.js` 现有 **28 项 jsdom 断言**将全部失效，**必须随本次改动重写**（CLAUDE.md：改原型后必须跑通）
- 已实现的 phase1 前后端界面口径将与新原型不一致；**本次不改后端代码**，差异在交付报告中列清单，由用户决定何时跟进
- 替换后 `docs/prototype.html` 仍是唯一「界面的事实来源」

### 我自行裁定的实现层假设（记录在案，可推翻）

| 假设 | 理由 |
|---|---|
| 「智能体空间」沿用中性称谓 **工作空间 / 项目**，不叫 AgentSpace | AgentSpace 是阿里云商业产品的资源模型概念 |
| 单文件 HTML，无构建、无外部 JS 框架，仅引 Google Fonts（与现有原型一致） | 保持原型可直接双击打开、可被 jsdom 加载做断言 |
| 演示数据为静态内置，不发任何网络请求 | 原型定位；也便于 smoke 断言稳定 |
| 打分公式、α=0.8 / β=0.2 / τ=0.75 / k=3（关键链路 5）、Average / pass@k / pass^k 三口径、指标 92 条 12 组 —— 全部照抄外层文档，原型只消费不改写 | 项目 CLAUDE.md 红线 |
