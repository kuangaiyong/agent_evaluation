## Purpose

把被测智能体的一次执行还原成可读、可定位、可作为判分依据的轨迹。评测平台的结论必须能回答「凭什么这么判」，轨迹就是那个凭据，因此这项能力是整个平台的地基。

## ADDED Requirements

### Requirement: 轨迹列表查询

系统 SHALL 提供 Trace 列表，每行呈现 Trace ID、Session ID、应用、模型、开始时间、耗时、Token、状态与 Score。

#### Scenario: 按应用与状态筛选

- **WHEN** 用户选择应用或执行状态
- **THEN** 列表只保留匹配的行，并显示命中数与总数
- **AND** 多个筛选条件之间取交集

#### Scenario: 按 ID 搜索

- **WHEN** 用户输入 Trace ID 或 Session ID 的片段
- **THEN** 列表只保留包含该片段的行

#### Scenario: 无匹配结果

- **WHEN** 筛选条件没有命中任何行
- **THEN** 列表区域显示空态说明，而不是留白

#### Scenario: 按数值列排序

- **WHEN** 用户点击 Token、耗时或 Score 列的表头
- **THEN** 列表按该列数值重排，再次点击切换升降序

### Requirement: 轨迹详情下钻

系统 SHALL 支持从列表下钻到单条轨迹详情，详情至少包含轨迹树、Session 回放与评估结果三个视图。

#### Scenario: 轨迹树还原执行路径

- **WHEN** 用户打开某条轨迹的轨迹树
- **THEN** 按顺序呈现用户输入、模型推理、工具调用、检索增强、决策分支与最终回复各步
- **AND** 每步标明耗时与 Token 消耗

#### Scenario: 从详情返回列表

- **WHEN** 用户在详情页点击返回
- **THEN** 回到轨迹列表，且导航仍高亮「AI Agent 可观测」

### Requirement: 判分依据可追溯

系统 SHALL 在评估结果视图中呈现每个评估器的得分、版本、判定依据与是否失败，并 SHALL 显式还原综合判定的算式与门槛。

#### Scenario: 逐项判定依据

- **WHEN** 用户查看某条轨迹的评估结果
- **THEN** 每个评估器一行，含 Score、版本与文字形式的判定依据
- **AND** 安全类评估器的结果以 0/1 门控形式呈现

#### Scenario: 综合判定可复算

- **WHEN** 用户查看综合判定
- **THEN** 界面显示打分算式、代入的各项数值、结果与通过门槛
- **AND** 同时呈现 Average、pass@k、pass^k 三个口径及试次数 k

### Requirement: 不做运维排障视图

系统 SHALL NOT 提供链路拓扑图与推理轨迹重建视图。

#### Scenario: 视图范围限定

- **WHEN** 用户在轨迹详情页切换视图
- **THEN** 只有轨迹树、Session 回放、评估结果三个页签
- **AND** 判分所需的是定位到某一步的证据，而非全局拓扑
