# 销售研究智能体与 Sales Research Bench（技术论文）

> **原文来源**：Microsoft Dynamics 365 Blog —— *Sales Research Agent & Sales Research Bench*
> **原文链接**：<https://www.microsoft.com/en-us/dynamics-365/blog/it-professional/2025/10/21/sales-research-agent-sales-research-bench/>
> **发布日期**：2025 年 10 月 21 日
> **补充**：素材清单原给的链接 <https://techcommunity.microsoft.com/blog/microsoft365copilotblog/sales-agent-in-microsoft-365-copilot-evaluation-results-%E2%80%93-technical-report/4476867> 抓取时返回 HTTP 403，故回溯到微软官方博客的一手技术论文
> **抓取日期**：2026-08-08
> **说明**：本文为原文全文中译，未作删改与解读。代码、SQL 与 JSON 数据结构保留原样不译。版权归微软所有，此处仅供部门内部学习参考。

---

### 把企业 AI 的标准提上去

Dynamics 365 Sales 中的**销售研究智能体（Sales Research Agent）**会自动连接实时 CRM 数据，也能连接存放在别处的其他数据，例如预算与目标。它能带着深厚的领域专长在复杂的、被定制过的 schema 上做推理，并通过文本叙述与丰富的数据可视化，针对当下的业务问题给出新颖的、可直接用于决策的洞察。

对销售负责人而言，这意味着他们可以自助地构建丰富的研究路径，横跨 CRM 与其他领域——这些事情过去要多人耗费数天甚至数周才能汇总出来——并且借助 AI 的能力，在管道、营收达成等关键议题上获得更深的洞察。

但市场上充斥着各种方案，它们是否真能提供足以支撑业务决策的质量水平，并不确定。业务负责人如何判断什么才是真正的企业级就绪？为了确保客户不必依赖个案传闻或"凭感觉"，**任何提供 AI 方案的厂商都必须通过清晰、可重复的指标赢得信任**，这些指标要展示质量、指出 AI 在哪里表现出色、在哪里需要改进、以及与替代方案相比处于什么位置。

*图 1. Dynamics 365 Sales Hub 中的销售研究智能体。*

本文介绍微软销售研究智能体背后的架构、评测方法论与评测结果。从多智能体编排、多模型支持，到 schema 智能、自我纠错与校验等先进技术，这些技术创新使销售研究智能体区别于市面上的其他方案。在思考如何最好地评测销售研究智能体时，微软审视了现有的 AI 基准，最终决定创建 **Sales Research Bench**——一个专门为衡量"基于业务数据的 AI 销售研究"质量而建的新基准，并与销售负责人的业务问题、需求与优先级保持一致。在 **2025 年 10 月 19 日**完成的正面对比评测中，销售研究智能体在百分制下**领先 Claude Sonnet 4.5 共 13 分，领先 ChatGPT-5 共 24.1 分**。

*图 2. Sales Research Bench 综合得分结果。*

**¹ 结果说明：** 结果反映的是 2025 年 10 月 19 日完成的测试，应用 Sales Research Bench 方法论评测了微软的销售研究智能体（Dynamics 365 Sales 的一部分）、OpenAI 的 ChatGPT（使用 ChatGPT Pro 授权，GPT-5 处于 Auto 模式）、以及 Anthropic 的 Claude Sonnet 4.5（使用 Claude Max 授权）。

**方法论与评测维度：** Sales Research Bench 包含 **200 个**与销售负责人相关的业务研究问题，跑在一个样例定制数据 schema 上。每个 AI 方案都通过与其架构相适配的不同访问机制获得对样例数据集的访问权。每个 AI 方案针对每个业务问题所生成的回复（含文本与数据可视化）都由 **LLM 判官**评判。我们基于 8 个维度评估质量，并根据客户的定性反馈——即客户表示他们在销售研究类 AI 工具中最看重什么——对各维度加权：**文本有据性（25%）、图表有据性（25%）、文本相关性（13%）、可解释性（12%）、Schema 准确性（10%）、图表相关性（5%）、图表选型（5%）、图表清晰度（5%）**。每个维度由 LLM 判官打分，**20 分为最差，100 分为最好**。举例来说，如果图表清晰锐利且标注良好，LLM 判官会给图表清晰度 100 分；如果图表不可读或具有误导性，则给 20 分。文本有据性与文本相关性使用 Azure Foundry 开箱即用的 LLM 评估器，其余六个维度的评判则使用 OpenAI 的 GPT 4.1 模型并配以专门的指引。综合总分由 8 个维度得分加权平均计算得出。方法论的更多细节见本文后续部分。

微软将继续使用 Sales Research Bench 中的评测来驱动销售研究智能体的持续改进，并计划在未来几个月内发布完整的评测包，以便其他人可以运行它来验证已发布的结果，或对他们自己使用的智能体做基准测试（本文中包含了该基准的示例评测）。

---

#### 销售研究智能体的架构

销售研究智能体的架构使其区别于其他方案，同时带来技术创新与业务价值。

1. **多智能体编排：** 销售研究智能体使用动态的多智能体基础设施，编排研究蓝图、文本叙述与数据可视化的生成，并附带对智能体工作过程的解释。在这条路径的每一步都会调用专门的智能体，以针对用户问题交付领域优化的洞察，同时把组织数据、业务与用户上下文都纳入考量。

2. **多模型支持：** 这套多智能体基础设施使得每个专门智能体都能使用最适合当前任务的模型。微软会测试每个专门智能体在不同模型下的表现。模型可以轻松替换，从而随着可用模型的演进持续优化销售研究智能体的质量。

3. **对业务语言的支持：** 业务语言（业务用户自然的沟通方式）与自然语言（任何非代码的语言）是有区别的。销售研究智能体能对业务语言的提示给出高质量回答，因为它会**把提示拆解成多个子问题**，构建研究计划，并在互联的数据源上做多步推理。此外，销售研究智能体被注入了销售领域的知识，因此能正确解读那些在用户提示中只是隐含存在的术语与上下文。

4. **Schema 智能：** 销售研究智能体既能处理开箱即用的企业 schema，也能处理被定制过的 schema，适应复杂的真实环境。它内置了成熟的技术与启发式方法，用以识别与用户查询相关的表和列。

5. **自我纠错与校验：** 销售研究智能体为其生成的回复内置了先进的自动纠错机制。无论产出的是 SQL 还是 Python 代码，智能体都会借助成熟的代码纠正器进行迭代式打磨——按需审查、校验并修订输出。**纠错循环先从一个快速的、非推理模型开始**，识别并修复直白的问题；如果错误仍然存在，系统会**升级到推理模型**，必要时再升级到**更强大的模型**，以确保更深的上下文理解与精确的纠正。这种动态的多模型流程有助于确保最终代码既准确又可靠，提升智能体洞察与建议的整体质量与可信度。

6. **可解释性：** 系统会记录每一次智能体交互与决策，以及为生成研究蓝图而产出的 SQL 查询和 Python 代码。销售研究智能体利用这些信息帮助用户快速核验其准确性并追溯其推理过程。每份蓝图都包含 **Show Work（展示工作过程）**——面向业务用户的简明语言解释，以及面向技术用户的 SQL 查询高级视图与更多细节。

*图 3. 销售研究智能体架构及其如何接入业务流程的高层示意图*

#### 为什么企业销售需要一套新的评测框架

在传统软件里，单元测试给出可重复的证据，证明核心行为可用并持续可用。对于 AI 方案，则需要**评测（evals）**来证明质量并跟踪长期的持续改进。

**企业理应获得为其需求量身定制的评测。** 尽管 AI 评测领域已有大量开创性工作，现有基准仍缺失了若干关键属性，而这些属性是一个 AI 方案要指导关键业务决策所必需的：

- 基准必须反映销售负责人用他们的**业务语言**提出的、战略性的、多面向的业务问题。
- 基准必须衡量 **schema 准确性**：即系统在可能被高度定制的记录系统 schema 上，是否正确处理了表、列与连接。
- 基准应当同时评估**文本叙述与数据可视化**两类洞察，因为这正是负责人据以决策的产物形态。

#### 为 AI 驱动的销售研究引入 Sales Research Bench

为满足这些要求，微软开发了 **Sales Research Bench**——一个综合质量分，用于评测 AI 驱动的销售研究方案，并与客户实际的问题、环境与优先级紧密对齐。通过与跨行业、跨地域的客户销售团队打交道，微软识别出了质量的关键维度，并用销售负责人使用的语言创建了真实的业务问题。评测所依托的数据 schema 经过定制，以反映客户企业环境的复杂性，包括其层层叠叠的业务逻辑与微妙的运营现实。最终得到的是一个严格的基准，它给出**基于 8 个加权维度的综合分**，同时给出**各维度的单项得分**，以揭示智能体在哪里表现出色、在哪里需要改进。

#### 基准方法论

Sales Research Bench 的评测基础设施包括：

- **评测数据集：** 200 个用销售负责人语言表述的业务问题，每一个都配有自己的一组**金标准答案**用于校验。
- **样例企业数据集：** 评测问题跑在一个定制 schema 上，以反映企业环境的复杂性。
- **评估器：** 基于 LLM 判官的评测，针对下述 8 个质量维度分别定制。文本有据性与文本相关性使用 Azure Foundry 开箱即用的评估器。其余 6 个维度使用 OpenAI 的 GPT 4.1 模型，并提供了具体的打分指引（见附录）。

以下是 200 个评测问题中的 3 个，均来自真实的销售负责人提问：

- 在已关闭的商机中，哪些销售人员在"Corporate Offices"业务分部里的实际总销售额与首年预估价值之间差距最大？
- 我们的销售投入是集中在特定行业，还是均匀分布在各行业？
- 相比我账面上的人头数（30 人），实际在岗并且在产出管道的有多少人？

#### 质量的各个维度

Sales Research Bench 汇总八个质量维度，按下列括号中的权重加权，以反映我们在与客户接触中听到的、客户在销售研究类 AI 工具中最看重的东西。

- **文本有据性（25%）**：确保叙述准确、忠实于样例企业数据，并应用了正确的业务定义。
- **图表有据性（25%）**：校验图表准确地表达了同一企业数据集中的底层数据。
- **文本相关性（13%）**：衡量文本叙述中的洞察与业务问题的相关程度。
- **可解释性（12%）**：确保 AI 方案准确、清晰地解释了它是如何得出这些回复的。
- **Schema 准确性（10%）**：通过评估生成的 SQL 查询是否与金标准答案中的表、连接与列一致，来核验表与列的选择是否正确。（**业务应用通常包含约 1000 张表，其中许多表有约 200 个列，而且全都可能被客户高度定制。**）
- **图表相关性（5%）**：校验图表中展示的数据与分析是否与业务问题相关。
- **图表选型（5%）**：评估所选的可视化形式是否匹配分析需求（例如趋势用折线、对比用柱状）。
- **图表清晰度（5%）**：评估可读性、标注、可访问性与图表整洁度。

每个维度由 LLM 判官打分，**20 分为最差，100 分为最好**。举例来说，如果图表清晰锐利且标注良好，LLM 判官会给图表清晰度 100 分；如果图表不可读或具有误导性，则给 20 分。

#### 样例企业数据集

**评测需要有代表性的条件才有用。** 通过与客户的接触，微软从高度定制的 schema、复杂的连接与过滤、以及微妙的业务逻辑（例如管道覆盖率与达成率的计算）中识别出了大量边界情况。

举例来说，大多数客户会用自定义表和自定义列来定制自己的 schema，比如用一张行业表替代行业列并把它链接到客户对象，或者添加"市场"和"业务分部"字段而不是使用已有的分部字段。结果是，他们的环境中往往**同时存在开箱即用的表列和定制的表列，而且名字还很相似**。通过系统性地把这些边界情况纳入样例定制 schema，Sales Research Bench 得以评测智能体在"理想路径"之外的表现，从而考察企业级就绪程度。

*图 4. 评测样例（更多示例见附录）*

#### 评测销售研究智能体与其他方案

除销售研究智能体外，微软还评测了 OpenAI 的 ChatGPT（使用 Pro 授权，GPT-5 处于 Auto 模式）与 Anthropic 的 Claude Sonnet 4.5（使用 Max 授权）。选择这些授权是为了让质量最优化：ChatGPT 的定价页把 Pro 描述为"完整访问 ChatGPT 的最佳能力"，而 Claude 的定价页则推荐 Max 以"最大化发挥 Claude 的能力"。¹ 同样地，ChatGPT 的评测使用 Auto 模式运行，该设置允许 ChatGPT 系统为每个提示自行判定最合适的模型变体。

微软实现了一个**受控的评测环境**，其中所有系统——**销售研究智能体**、**ChatGPT-5** 与 **Claude Sonnet 4.5**——都使用**完全相同的问题与数据**，只是通过与各自架构相适配的不同访问机制。

**销售研究智能体**拥有一个**原生的多智能体编排层**，直接连接 Dynamics 365 Sales 数据。这使它能够自主发现 schema 关系与实体依赖，并在自己的编排栈内原生完成"自然语言到查询"的推理。

由于 ChatGPT 与 Claude 并不开箱支持关系型的业务线源系统，微软通过**将同一份数据集镜像到一个 Azure SQL 实例**来为它们开放访问。镜像过程保留了从 Dataverse 到 Azure SQL 的所有数据类型、主键、外键以及表间关系。这份 Azure SQL 副本通过 **MCP SQL connector** 暴露出来，确保 ChatGPT 与 Claude 取到的是**完全相同的数据**，只是经由一个标准化的外部接口。回复被采集之后，使用**同样的评估器、对照完全相同的评测细则**进行评判。

最后，发给 ChatGPT 与 Claude 的提示中包含了"创建图表"以及"解释如何得出答案"的指令（销售研究智能体自带这些功能）。

¹ [ChatGPT 定价](https://chatgpt.com/pricing?openaicom_referred=true) 与 [Claude 定价](https://claude.com/pricing)，均于 2025 年 10 月 19 日访问

#### 评测结果

在定制 schema 上的 200 个评测测试中，销售研究智能体在百分制下获得 **78.2** 分的综合得分，Claude Sonnet 4.5 获得 **65.2** 分，ChatGPT-5 获得 **54.1** 分。

*图 5. Sales Research Bench 综合得分（堆叠柱状图中叠加了各维度得分）。*

进一步拆解：销售研究智能体在全部 8 个维度上都优于其他方案，**差距最大的是图表相关的维度**（有据性、选型、清晰度与相关性），**差距最小的是 schema 准确性与文本有据性**。Claude Sonnet 4.5 在全部 8 个维度上都优于 ChatGPT-5，差距最大的是图表清晰度，最小的是图表相关性。

*图 6. Sales Research Bench 各维度得分。*

#### 展望

销售研究智能体带来了新一代 AI 优先的业务应用，改变了销售负责人处理与解决复杂业务问题的方式。Sales Research Bench 与之并行创建，代表了企业 AI 评测的新标准：严格、全面，并与销售负责人的需求和优先级对齐。

Sales Research Bench 的后续计划包括：用该基准持续改进销售研究智能体、与更广泛的竞品做进一步对比、以及发布评测包以便客户自行运行、验证已发布结果并对他们所用的智能体做基准测试。**评测不是一次性事件。分数可以跨版本跟踪，以确保 AI 方案不断演进以满足客户需求。**

在 Sales Research Bench 之外，微软计划为更多业务职能与智能体方案开发评测框架与基准——客服、财务及其他领域。目标是为企业 AI 的信任与透明度树立新标准。

---

#### 附录

**提供给 LLM 判官的打分指引**

文本有据性与文本相关性使用 Azure Foundry 开箱即用的 LLM 评估器。以下是为其余六个质量维度提供给 LLM 判官的指引。这些判官使用 OpenAI 的 GPT 4.1 模型。

**Schema 准确性：**

- **100**：完美匹配——所有金标准表与列都在（多出的列可以接受，Dynamics 等价物可以接受）
- **80**：很好——少量列缺失，或缺一张表
- **60**：良好——有一些重要的列或表缺失，但核心 schema 在
- **40**：一般——schema 差异显著，但有部分重叠
- **20**：差——严重的 schema 不匹配，或完全是另一批表

**可解释性：**

- **100（优秀）**：解释高度详尽，完美描述了生成的 SQL 在做什么，技术上准确，并提供了清晰的业务上下文
- **80（良好）**：解释足够详尽且基本准确，在描述 SQL 操作时有少量缺口
- **60（一般）**：解释提供了足够的细节，但遗漏了一些重要的 SQL 操作，或存在少量不准确之处
- **40（差）**：解释缺乏足以理解 SQL 操作的细节，或存在显著的不准确
- **20（很差）**：解释过于含糊、大部分不正确，或对生成的 SQL 提供的细节严重不足

**图表有据性：**

- **100**：数据与金标准准确匹配，**或**金标准与图表两者皆为空
- **80**：少量数据不准确
- **60**：有一些数据不准确
- **40**：严重的数据不准确
- **20**：数据与金标准完全不符

**图表相关性：**

- **100**：问题与图表相互强化，**或**金标准与图表两者皆为空
- **60**：问题与图表大致对齐，但存在一些脱节
- **20**：问题与图表完全不对齐

**图表选型：**

- **100**：对该任务而言是最优的图表选择，**或**金标准与图表两者皆为空（恰当的留空）
- **60**：可接受的图表选择，但对该任务不是最优
- **20**：不恰当 / 令人困惑的图表类型

**图表清晰度：**

- **100**：图表清晰锐利且标注良好，**或**金标准与图表两者皆为空
- **60**：图表可读，但缺少标注 / 清晰度要素
- **20**：图表不可读、具有误导性

---

**评测数据集示例：**

以下是我们用来针对上述全部评测细则对销售研究智能体做基准测试的部分评测数据集。这些相同的问题也被用于评测竞品方案。

**评测数据集之一**

> 原文问题：*Looking at closed opportunities, which sellers have the largest gap between Total Actual Sales and Est Value First Year in the 'Corporate Offices' Business Segment?*
> 中译：在已关闭的商机中，哪些销售人员在"Corporate Offices"业务分部里的实际总销售额与首年预估价值之间差距最大？
> 难度：**hard**
> 标签：`seller-performance`、`variance`、`actuals-vs-estimate`

```sql
SELECT su.[fullname] AS [seller_name],
       COUNT(*) AS [closed_deals],
       SUM(CAST(COALESCE(o.[sop_totalactualsales], o.[actualvalue_base]) AS DECIMAL(38,2))) AS [total_actual_sales],
       SUM(CAST(o.[sop_estvaluefirstyear_base] AS DECIMAL(38,2))) AS [total_est_value_first_year],
       SUM(CAST(COALESCE(o.[sop_totalactualsales], o.[actualvalue_base]) AS DECIMAL(38,2)))
         - SUM(CAST(o.[sop_estvaluefirstyear_base] AS DECIMAL(38,2))) AS [sales_gap]
FROM [dbo].[opportunity] AS o
JOIN [dbo].[systemuser] AS su ON CAST(o.[ownerid] AS NVARCHAR(36)) = CAST(su.[systemuserid] AS NVARCHAR(36))
JOIN [dbo].[sop_businesssegment] AS bs ON CAST(o.[sop_businesssegment] AS NVARCHAR(36)) = CAST(bs.[sop_businesssegmentid] AS NVARCHAR(36))
WHERE o.[statecodename] = 'Won' AND bs.[sop_name] = 'Corporate Offices' AND su.[fullname] <> '' AND o.[sop_estvaluefirstyear_base] IS NOT NULL
GROUP BY su.[fullname]
HAVING SUM(CAST(COALESCE(o.[sop_totalactualsales], o.[actualvalue_base]) AS DECIMAL(38,2))) IS NOT NULL
ORDER BY [sales_gap] DESC;
```

金标准（结构化）：

| seller_name | closed_deals | total_actual_sales | total_est_value_first_year | sales_gap |
|---|---|---|---|---|
| Jenny Chambers | 3 | 44501.69 | 16010.15 | 28491.54 |
| Heather Rogers | 1 | 21501.05 | 4190.57 | 17310.48 |
| Grace Rice | 1 | 21223.33 | 6789.20 | 14434.13 |
| Ann Rice | 1 | 3243.23 | 7267.77 | -4024.54 |

金标准（非结构化文本）：正差距最大的是 Jenny Chambers（+$28.49K）、Heather Rogers（+$17.31K）与 Grace Rice（+$14.43K）。Ann Rice 低于预估（−$4.02K）。

评测说明：差距 = 实际总销售额 − 首年预估；仅限 Corporate Offices 分部；仅限已关闭（Won）的商机。

**评测数据集之二**

> 原文问题：*Are our sales efforts concentrated on specific industries or spread evenly across industries?*
> 中译：我们的销售投入是集中在特定行业，还是均匀分布在各行业？
> 难度：**medium**
> 标签：`industry`、`concentration`、`open-vs-total`

```sql
SELECT
    [sop_industry].[sop_name] AS [industry_name],
    COUNT([opportunity].[opportunityid]) AS [total_opportunity_count],
    COUNT(CASE
              WHEN [opportunity].[statecodename] NOT IN ('Won','Lost','Canceled')
              THEN 1
         END) AS [open_opportunity_count]
FROM
    [opportunity]
INNER JOIN
    [account] ON CAST([opportunity].[parentaccountid] AS NVARCHAR(36)) = CAST([account].[accountid] AS NVARCHAR(36))
INNER JOIN
    [sop_industry] ON CAST([account].[sop_industry] AS NVARCHAR(36)) = CAST([sop_industry].[sop_industryid] AS NVARCHAR(36))
GROUP BY
    [sop_industry].[sop_name]
HAVING
    COUNT([opportunity].[opportunityid]) > 0
ORDER BY
    [open_opportunity_count] DESC;
```

金标准（结构化，节选自 23 行）：

| industry_name | total_opportunity_count | open_opportunity_count |
|---|---|---|
| Legal Services | 1352 | 240 |
| Insurance | 1210 | 212 |
| Non-Durable Merchandise Retail | 946 | 177 |
| Inbound Repair and Services | 695 | 126 |
| Outbound Consumer Service | 740 | 124 |
| Design, Direction and Creative Management | 719 | 119 |
| Building Supply Retail | 633 | 118 |
| Durable Manufacturing | 569 | 111 |
| Business Services | 597 | 108 |
| Broadcasting Printing and Publishing | 597 | 104 |
| Accounting | 551 | 104 |
| Distributors, Dispatchers and Processors | 562 | 104 |
| Financial | 606 | 102 |
| Consulting | 532 | 100 |
| Agriculture and Non-petrol Natural Resource Extraction | 586 | 95 |
| Doctor's Offices and Clinics | 497 | 90 |
| Brokers | 579 | 90 |
| Food and Tobacco Processing | 489 | 86 |
| Consumer Services | 451 | 81 |
| Eating and Drinking Places | 448 | 76 |
| Equipment Rental and Leasing | 425 | 74 |
| Entertainment Retail | 429 | 73 |
| Inbound Capital Intensive Processing | 419 | 71 |

金标准（非结构化文本）：投入面很广但有倾斜：Legal Services 与 Insurance 的商机总数最多，同时有若干行业维持着 70–120 个开放商机。

评测说明：按行业统计商机总数与开放数；按开放数排序。

**评测数据集之三**

> 原文问题：*Compared to my headcount on paper (30), how many people are actually in seat and generating pipeline?*
> 中译：相比我账面上的人头数（30 人），实际在岗并且在产出管道的有多少人？
> 难度：**medium**
> 标签：`capacity`、`headcount`、`pipeline`

```sql
WITH open_opps AS (
  SELECT o.*
  FROM opportunity o
  WHERE o.statecodename NOT IN ('Won','Lost','Canceled')
)
SELECT
  CAST(30 AS INT) AS headcount_on_paper,
  COUNT(DISTINCT open_opps.ownerid) AS active_pipeline_users,
  (30 - COUNT(DISTINCT open_opps.ownerid)) AS delta_needed,
  (SELECT COUNT(*) FROM opportunity) AS total_opportunities,
  (SELECT COUNT(*) FROM open_opps) AS open_opportunities,
  (SELECT SUM(CAST(o2.estimatedvalue_base AS DECIMAL(38,2))) FROM open_opps o2) AS open_pipeline_value;
```

金标准（结构化）：

| headcount_on_paper | active_pipeline_users | delta_needed | total_opportunities | open_opportunities | open_pipeline_value |
|---|---|---|---|---|---|
| 30 | 7 | 23 | 14860 | 2662 | 16047760.29 |

金标准（非结构化文本）：面对 30 人的计划编制，只有 7 名销售有活跃管道（缺口 23 人）。开放管道总额为 $16.05M，分布在 2662 个商机上。

评测说明：活跃销售按当前管道上的去重 owner 计数。
