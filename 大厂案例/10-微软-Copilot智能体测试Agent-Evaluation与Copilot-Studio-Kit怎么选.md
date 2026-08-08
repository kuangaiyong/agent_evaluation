# 测试 Copilot 智能体：什么时候用 Agent Evaluation，什么时候用 Copilot Studio Kit

> **原文来源**：Holger Imbery 个人博客（Microsoft MVP）—— *Testing Copilot Agents: When to Use Agent Evaluation vs. the Copilot Studio Kit*
> **原文链接**：<https://holgerimbery.blog/testing-copilot-agents-when-to-use-agent-evaluation-vs-the-copilot-studio-kit>
> **发布日期**：2026 年 4 月 5 日（阅读时长 9 分钟）
> **相关**：微软 2026 年 3 月 31 日 Agent Evaluation GA 公告；前作《Testing Copilot Studio Agents: Copilot Studio Kit vs. Agent Evaluation (Preview)》的更新版
> **抓取日期**：2026-08-08
> **说明**：本文为原文全文中译，未作删改与解读。版权归原作者所有，此处仅供部门内部学习参考。

---

2026 年 3 月 31 日，微软发布了正式可用（GA）的 Agent Evaluation，从根本上改变了团队验证 Copilot 智能体的方式。本文说明 Agent Evaluation 与 Copilot Studio Kit 在质量保障策略中分别扮演什么样的角色——两者不同，但互补——以及各自应在何时使用。

## 目录

微软在 Agent Evaluation（GA）中交付了什么 · 核心特征（截至 2026 年 3 月 31 日）· 评测能力 · Copilot Studio Kit 为测试提供了什么 · 明确的测试能力 · 执行与自动化 · 测试之外的企业级扩展 · 直接对比 · 两者是什么关系（这是关键洞察）· 给企业团队的实操结论 · 各自何时使用 · 它们如何互补 · 结论

## 摘要导语

**Agent Evaluation 与 Copilot Studio Kit 不是互相竞争的工具——它们代表的是一套分层的质量保障策略。** Agent Evaluation 提供快速的、AI 辅助的行为验证，直接嵌在 Copilot Studio 里，适合迭代与快速反馈。Copilot Studio Kit 则为生产门禁、合规与治理提供确定性的、企业级的验证。本文拆解各自做什么、何时用，以及随着智能体质量成熟应如何同时采用两者。

## 为什么要读这篇

如果你正在组织内构建或规模化 Copilot 智能体，你需要一个清晰的测试策略。本文剥开各种定位话术，给出一个实用的决策框架：什么时候该拿 Agent Evaluation，什么时候该拿 Copilot Studio Kit，并配以真实场景，展示成熟团队如何在开发生命周期中分层使用这两个工具。

## 微软在 Agent Evaluation（GA）中交付了什么

2026 年 3 月 31 日，微软宣布 Agent Evaluation 正式可用，这是 Copilot Studio 测试与验证能力上的一个重要里程碑。Agent Evaluation 现已全面可用，并且**直接内置在 Copilot Studio 中**。它的目标是让智能体质量变得**可见、可重复、可规模化，而不需要外部工具或额外搭建**。这次 GA 发布是微软推动"智能体质量保障平民化"努力的集大成——把此前只有高级配置才能用上的评测能力，直接交到 Copilot Studio 创作环境里每一位普通创作者手中。

### 核心特征（截至 2026 年 3 月 31 日）

**直接集成进 Copilot Studio 的创作体验**

Agent Evaluation 不是一个独立工具或外部服务。它就活在构建智能体的那个 Copilot Studio 界面里，让创作者无需切换上下文、无需复杂集成即可验证自己的智能体。这种紧密集成降低了摩擦，鼓励在开发周期中频繁验证。

**为回答那个生产问题而设计：**

> **"我们能不能信任这个智能体，让它行为正确、一致且安全？"**

这个核心问题驱动了整个设计哲学。Agent Evaluation 聚焦于**行为置信度**——即智能体在多样化的场景与用户输入下，是否产出恰当、一致且安全的回复。

**取代无法规模化的人工测试与抽查**

在 Agent Evaluation 之前，智能体验证严重依赖人工测试：逐个测试场景、逐条查看回复、并寄希望于覆盖率够用。这种做法无法随智能体的复杂度或使用量而扩展。Agent Evaluation 通过 AI 辅助评测与可复用测试集，把这个过程自动化并规模化。

**设计用于上线前，以及每次变更后的持续验证**

Agent Evaluation 不是一次性的闸门。它是为**持续验证**设计的：首次上线之前、部署更新之前，以及生产中对话持续流经系统时。这种从"仪式性测试"到"持续验证"的转变，与现代 DevOps 实践相一致。

### 评测能力

Agent Evaluation 允许创作者：

- **创建评测集**，来源包括：
  - 手工添加的问题
  - 导入的测试集
  - **由智能体元数据与知识源派生出的 AI 生成查询**
- **选择灵活的评测方法**，包括：
  - 精确 / 部分匹配
  - 语义相似度
  - 意图识别
  - 相关性与完整性打分
- 混合 AI 生成场景与人工定义场景，在广度与深度之间取得平衡
- 长期复用这些评测，并**通过 API 运行**以支持全生命周期测试

**关键定位：**

Agent Evaluation 被定位为一个**轻量的、AI 辅助的验证层**，自然嵌入日常的智能体创作与迭代之中。不同于那些需要切换上下文与专门基础设施的重型外部测试框架，Agent Evaluation 就在构建智能体的 Copilot Studio 内部运行。这种内嵌式做法承认了一个现实：智能体创作者在快速迭代、在每一步都要全面测试，并且需要在自己的创作流里就拿到验证反馈，而不是把它变成生产后的瓶颈。AI 辅助打分意味着创作者不必手写每一条测试用例、也不必事先定义复杂的评分细则；他们可以从智能体自身的知识源与元数据生成相关的测试场景，再加以打磨。这让评测对各种水平的创作者都可用，并且能随智能体复杂度一起扩展。

## Copilot Studio Kit 为测试提供了什么

Copilot Studio Kit（Power CAT）是一个**独立的、基于解决方案的工具包**，为 Copilot Studio 增补企业级的测试、治理与分析能力。它由微软 Power CAT（Patterns and Practices）团队开发，是一个成熟的、可用于生产的框架，面向那些需要严格质量保障、监管合规与可规模化 CI/CD 集成的组织。Agent Evaluation 处理的是创作画布内的日常迭代与行为置信度，而 Copilot Studio Kit 提供的是结构性骨架，服务于那些需要**确定性验证、审计轨迹、多层测试编排、以及大规模部署下的治理执行**的组织。

### 明确的测试能力

Kit 支持结构化的、确定性的、多层次的测试，包括：

- **Response Match**（精确或条件式文本比对）
- **Attachment Match**（自适应卡片 / 文件）
- **Topic Match**（需要 Dataverse 增强）
- **Generative Answer 评测**，使用 AI Builder 与评分细则（rubric）
- **多轮测试**，跑在共享的会话上下文里
- **Plan Validation**（面向生成式编排）——**校验实际调用了哪些工具/动作，而不只是看智能体说了什么**

### 执行与自动化

- 测试通过 Copilot Studio API（Direct Line）执行
- 通过 Excel 导入导出做批量创建与维护
- 详尽的运行级遥测：
  - 通过 / 失败
  - 延迟
  - 观测到的回复
  - 聚合指标
- 结果可用以下方式增强：
  - Azure Application Insights
  - Dataverse 会话转录本

### 测试之外的企业级扩展

Kit 还包含：

- 面向 Power BI 的会话 KPI
- Prompt Advisor（提示词顾问）
- Agent Inventory（智能体清册）
- Agent Review Tool（智能体评审工具）
- Compliance Hub（合规中心），带策略执行与 SLA 驱动的评审

**关键定位：**

Copilot Studio Kit 是为**验证、回归测试、生产门禁与规模化治理**而建的。不同于 Agent Evaluation 那种活在创作画布内的轻量 AI 辅助方式，Kit 的角色是**企业测试骨干**，面向那些要求确定性验证、完整审计轨迹与监管合规执行的组织。它衔接了开发期验证与生产就绪之间的鸿沟，使得结构化的质量门禁能够与企业 DevOps 流水线对齐。Kit 对精确回复匹配、话题校验与编排计划验证的强调，使它成为关键任务部署的必需品——在这些场景中，智能体行为必须可预测、可追溯、可合规。

## 直接对比

| 维度 | Agent Evaluation（GA） | Copilot Studio Kit |
|---|---|---|
| 位于何处 | 内置于 Copilot Studio 界面 | 独立的 Power CAT 解决方案 |
| 主要目的 | **行为验证** | **功能验证** |
| 搭建成本 | 极小 | 较高（Dataverse、AI Builder，App Insights 可选） |
| 测试创建 | 手工、导入、AI 生成 | 手工 + Excel 批量 |
| AI 辅助打分 | 是（核心特性） | 是（通过 AI Builder 的 Generative Answers） |
| 确定性检查 | 有限 | 强（精确匹配、话题、附件） |
| 多轮场景 | 未见明确文档 | 明确支持 |
| 编排计划验证 | 未见文档 | 明确支持 |
| CI/CD 与质量门禁 | 隐式 / 基于 API | 显式的流水线集成 |
| 治理与合规 | 不在范围内 | 一等特性 |

## 两者是什么关系（这是关键洞察）

**微软并没有用 Agent Evaluation 取代 Copilot Studio Kit。** 相反，各方资料显示的是一条清晰的**分层策略**：

> **Agent Evaluation**
> → 快速、AI 辅助、产品内验证
> → 适合早期反馈、迭代与持续信心
>
> **Copilot Studio Kit**
> → 深度、确定性、可自动化的验证
> → 适合发布门禁、回归测试、编排正确性与治理

这一定位在社区与微软的指引中也有明确体现：Agent Evaluation 填补的是人工测试无法规模化留下的空白，而 Kit 仍然是系统级的质量骨干。

## 给企业团队的实操结论

基于已明确文档化的内容：

### 各自何时使用

**Agent Evaluation 最适合：**

- 智能体开发期间的快速迭代周期
- 正式评审前的早期质量验证
- 无需基础设施复杂度的持续行为检查
- AI 辅助的语义评测已经够用的场景
- 反馈速度优先于确定性保证的团队
- 类似这样的问题："我上次改完之后，这个智能体整体表现还行吗？"
  → **用 Agent Evaluation。**

**Copilot Studio Kit 最适合：**

- 生产发布门禁与正式部署审批
- 更新推到生产之前的回归测试
- 需要审计轨迹的监管与合规场景
- 必须做确定性验证的关键任务智能体
- 需要校验计划与工具调用的复杂编排场景
- 需要端到端正确性的多轮对话
- 类似这样的问题："我们有没有搞坏什么？话题对不对？工具调没调？这个能发吗？"
  → **用 Copilot Studio Kit。**

### 它们如何互补

在成熟的配置里，两者是互补而非竞争的：

- **开发阶段**：Agent Evaluation 提供快速反馈回路以支持迭代
- **预生产阶段**：Copilot Studio Kit 执行确定性验证门禁
- **生产阶段**：两者都支持持续监控——Agent Evaluation 看行为趋势，Kit 做功能回归检测
- **治理阶段**：Kit 的合规与 KPI 跟踪提供企业审计轨迹与策略执行层

从单智能体项目扩张到企业级部署的组织，应当预期在不同成熟阶段先后采用这两个工具，**按顺序使用，而不是二选一**。

## 结论

Agent Evaluation 与 Copilot Studio Kit 代表了微软对"智能体测试成熟度曲线"给出的深思熟虑的答案。当组织把智能体从概念验证一路构建、迭代、扩张到关键任务系统时，这两个工具在生命周期的不同阶段各自扮演着必不可少的角色。

Agent Evaluation 把质量验证带进了创作体验之中，降低了日常迭代的摩擦，让所有智能体创作者都能获得行为置信度。它的 AI 辅助路线承认了快速开发周期的现实，以及对快速反馈回路的需求。

相比之下，Copilot Studio Kit 提供了企业所需的确定性骨干——精确验证、治理执行、监管合规，以及关键任务部署所必需的审计轨迹。

**关键洞察在于：这两个工具不是竞争者，而是互补品。** 团队应当按顺序采用它们：开发期先用 Agent Evaluation 做快速迭代，随着智能体逼近生产再叠加 Copilot Studio Kit。真正认真对待规模化智能体质量的组织，最终会两者都用，从构思到生产乃至更远，在每一个阶段建立信心。
