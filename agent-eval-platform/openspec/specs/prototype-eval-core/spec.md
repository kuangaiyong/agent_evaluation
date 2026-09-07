# prototype-eval-core Specification

## Purpose
定义评测主线五屏的契约：评估器（DeepEval 预置 + 自定义）、评估任务、分析洞察、Bad Case 库、实验与回归。这是平台的立身之本，也是与 phase1 差异最大的部分 —— 92 条指标字典已被 DeepEval 评估器取代。

## Requirements

### Requirement: 评估器分预置与自定义两类

`evaluators` 屏 SHALL 提供 `预置` 与 `自定义` 两个页签。预置页签 SHALL 列出 DeepEval 内置评估器，按 RAG / Agentic / 多轮会话 / 安全与质量 四组呈现，每条 SHALL 显示官方类名。

预置清单 SHALL 至少包含以下 16 个类名：`AnswerRelevancyMetric`、`FaithfulnessMetric`、`ContextualRelevancyMetric`、`ContextualPrecisionMetric`、`ContextualRecallMetric`、`TaskCompletionMetric`、`ToolCorrectnessMetric`、`ArgumentCorrectnessMetric`、`TurnRelevancyMetric`、`RoleAdherenceMetric`、`KnowledgeRetentionMetric`、`ConversationCompletenessMetric`、`HallucinationMetric`、`BiasMetric`、`ToxicityMetric`、`SummarizationMetric`。

原型 SHALL NOT 出现「指标字典」「指标库」屏或导航项，SHALL NOT 声称平台内置 92 条指标。

#### Scenario: 16 个 DeepEval 类名齐备

- **WHEN** 读取 `[data-screen="evaluators"]` 内的全部文本
- **THEN** 上述 16 个类名逐一命中，命中数均 ≥ 1

#### Scenario: 无指标字典残留

- **WHEN** 查询 `.nav-item[data-go="metrics"]`，并全文搜索「指标字典」「指标库」
- **THEN** 导航项返回 0 个元素，且两个词命中数均为 0

#### Scenario: 分组页签可切换

- **WHEN** 点击评估器屏内 `[data-tab="evgroup"]` 的各个页签
- **THEN** 每次点击后被选中项带 `.on`，且列表区显示的行数随分组变化

### Requirement: 自定义评估器支持 GEval 与 DAG

`自定义` 页签 SHALL 提供两种创建方式：`GEval`（自然语言 criteria）与 `DAGMetric`（决策树式确定性评分）。

#### Scenario: 两种自定义类型均可见

- **WHEN** 切换到 `自定义` 页签
- **THEN** 页面文本同时包含 `GEval` 与 `DAGMetric`

### Requirement: 评估器配置表单采用 DeepEval 真实参数且默认 τ=0.75

创建/编辑评估器的弹窗 SHALL 提供以下字段：`threshold`、`model`、`include_reason`、`strict_mode`、`async_mode`、`verbose_mode`。

`threshold` 的默认值 SHALL 为 `0.75`（平台口径 τ），SHALL NOT 为 DeepEval 默认的 `0.5`；表单内 SHALL 有一处说明文字点明这一差异。

#### Scenario: 阈值默认 0.75 而非 0.5

- **WHEN** 打开创建评估器弹窗
- **THEN** 名为 `threshold` 的输入控件其 `value` 为 `0.75`

#### Scenario: 六个 DeepEval 参数齐备

- **WHEN** 打开创建评估器弹窗
- **THEN** 弹窗内可查到 `threshold`、`model`、`include_reason`、`strict_mode`、`async_mode`、`verbose_mode` 六个字段名

### Requirement: 打分公式与三分量映射显式标注为待确认

原型 SHALL 在评估器或分析洞察屏展示打分公式 `task_score = s_safety × (α · s_completion + β · s_robustness)` 及取值 α=0.8、β=0.2、τ=0.75、k=3（关键链路 5）。

三分量到 DeepEval 评估器的映射 SHALL 带「待确认」标记，避免被当作既定口径。

#### Scenario: 公式与四个常量同时出现

- **WHEN** 读取原型全文
- **THEN** 同时命中 `s_safety`、`α`（或 `alpha`）、`0.8`、`0.2`、`0.75`，且命中 `pass@k` 与 `pass^k`

#### Scenario: 映射标注待确认

- **WHEN** 查询 `[data-map-status]`
- **THEN** 至少 1 个元素，其文本包含「待确认」

### Requirement: 评估任务的数据来源与运行策略

`tasks` 屏的新建任务弹窗 SHALL 为分步表单（至少 2 步：数据配置 → 选择评估器），并 SHALL 提供：

- 数据来源四选一：`链路` / `Agent 轨迹` / `日志` / `数据集`
- 评估粒度：`单轮对话` / `多轮对话`
- 运行策略：`基于新数据持续评估` / `基于历史数据评估`
- 采样比例与最大样本数
- 试次 k，默认 `3`

#### Scenario: 分步表单可前进可后退

- **WHEN** 打开新建评估任务弹窗，点击「下一步」再点击「上一步」
- **THEN** 步骤面板先切到第 2 步（第 1 步带 `hidden`），再切回第 1 步（第 2 步带 `hidden`）

#### Scenario: 四种数据来源齐备

- **WHEN** 打开新建评估任务弹窗第 1 步
- **THEN** `链路`、`Agent 轨迹`、`日志`、`数据集` 四个选项均存在

#### Scenario: 试次默认 3

- **WHEN** 打开新建评估任务弹窗
- **THEN** 试次输入控件的 `value` 为 `3`

### Requirement: 分析洞察三口径与三列分数

`insight` 屏 SHALL 同时呈现 `Average`、`pass@k`、`pass^k` 三个口径的结果，SHALL NOT 只报其中之一。

评估明细表 SHALL 含 `原始分数`、`分数范围`、`归一化分数` 三列 —— 各评估器制式不同，需归一化后才可汇总。

#### Scenario: 三口径同屏呈现

- **WHEN** 读取 `[data-screen="insight"]` 的文本
- **THEN** `Average`、`pass@k`、`pass^k` 三者均命中

#### Scenario: 明细表含三列分数

- **WHEN** 读取 `insight` 屏内明细表的表头
- **THEN** 表头文本包含 `原始分数`、`分数范围`、`归一化分数`

### Requirement: 低分样本可下钻并可入 Bad Case 库

分析洞察的明细行 SHALL 可下钻到链路详情屏 `trace`。低分样本 SHALL 提供「存入 Bad Case」的操作入口。

#### Scenario: 明细行下钻到链路详情

- **WHEN** 点击 `insight` 屏中带 `[data-drill^="trace:"]` 的行
- **THEN** `[data-screen="trace"]` 不带 `hidden`，其余屏均带 `hidden`

### Requirement: 实验与回归含门禁判定

`regression` 屏 SHALL 呈现基线与候选版本的对比，SHALL 显示门禁结论（通过 / 阻断），并 SHALL 以 τ=0.75 为判定线。对比图 SHALL 使用 bullet 图或等价形式表达「实测值 vs 阈值」。

#### Scenario: 门禁结论与阈值同时可见

- **WHEN** 读取 `[data-screen="regression"]` 的文本
- **THEN** 命中 `0.75`，且命中 `通过` 或 `阻断` 之一

#### Scenario: 存在 bullet 形式的阈值对比图

- **WHEN** 查询 `[data-screen="regression"] [data-chart="bullet"]`
- **THEN** 返回元素数 ≥ 1
