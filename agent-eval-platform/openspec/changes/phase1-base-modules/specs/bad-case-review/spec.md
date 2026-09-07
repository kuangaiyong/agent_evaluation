## Purpose

把低分样本交给人复核，并把复核结论沉淀成失败模式与回归素材。人工复核在这里不是兜底人力，而是评估器质量门禁唯一的真值来源。

## ADDED Requirements

### Requirement: Case 列表

系统 SHALL 呈现低分 Case 列表，每行含 Case ID、关联 Trace、应用、触发评估器、Score 与门槛、触发时间、复核状态与 Root Cause。

#### Scenario: 列含触发评估器与归因

- **WHEN** 用户查看 Bad Case 列表
- **THEN** 每行显示是哪个评估器触发的，以及已标注的 Root Cause
- **AND** 未复核的行 Root Cause 为空并标明待复核

#### Scenario: 超期可见

- **WHEN** 某待复核 Case 超过约定时长仍未处理
- **THEN** 该行标明已超期时长
- **AND** 概览区给出超期条数

### Requirement: 人工复核

系统 SHALL 支持对单条 Case 作出确认 Bad、误判、待定三种判定，并要求标注 Root Cause。复核结论 MUST 留痕复核人与时间。

#### Scenario: 单条复核

- **WHEN** 具备写权限的用户打开某条 Case 并提交判定
- **THEN** 系统记录判定、Root Cause、复核人与时间
- **AND** 列表中该行的复核状态同步更新

#### Scenario: 批量复核需同源

- **WHEN** 用户对一批 Case 作批量判定
- **THEN** 界面提示需确认这批 Case 的失败模式确实同源
- **AND** 批量结果同样逐条留痕

### Requirement: 失败模式聚类

系统 SHALL 按 Root Cause 对已确认的 Bad Case 归并并呈现分布。

#### Scenario: 归并分布可见

- **WHEN** 用户查看失败模式聚类
- **THEN** 按 Root Cause 给出条数分布，从高到低排列
- **AND** 用户可据此判断改一次 Prompt 能消掉多少 Case

### Requirement: 复核结论回流

复核结论 SHALL 作为评估器质量门禁的样本来源，并支持归集为回归素材。

#### Scenario: 回流质量门禁

- **WHEN** 一条 Case 完成复核
- **THEN** 该结论计入评估器与人工一致率的样本池

#### Scenario: 归集为数据集

- **WHEN** 用户导出已确认的 Bad Case
- **THEN** 系统生成对应的数据集条目
- **AND** 未补金标准的条目不参与门禁判定
