# prototype-governance Specification

## Purpose
定义支撑 1000 人规模的治理与系统能力契约：风险审计、操作审计、成本与配额、空间与成员、通知中心，以及总览与快速启动两屏。这些屏决定平台能否在多业务线共用时不互相干扰、成本可归属、变更可追溯。

## Requirements

### Requirement: 工作空间与成员管理

`space` 屏 SHALL 提供工作空间列表与成员列表。成员表 SHALL 含列：`成员`、`角色`、`所属空间`、`加入时间`。角色取值 SHALL 限于 `管理员` / `测试开发` / `测试工程师` / `只读` 四种。

空间设置类操作入口 SHALL 标注 `data-role-only="admin"`。

#### Scenario: 成员表角色取值受限

- **WHEN** 读取成员表「角色」列的全部取值
- **THEN** 每个取值均属于四种角色之一

#### Scenario: 非管理员看不到空间设置

- **WHEN** 将角色切换为 `tester` 并进入 `space` 屏
- **THEN** 该屏内 `[data-role-only="admin"]` 的元素全部带 `hidden`

### Requirement: 配额与用量

`budget` 屏 SHALL 按工作空间呈现配额与用量，SHALL 至少包含 `评测次数` 与 `Token 用量` 两类配额，SHALL 显示「已用 / 上限」与用量百分比，并 SHALL 在超阈时以 destructive 语义色标记。

配额单位 SHALL NOT 使用「AI 积分」。

#### Scenario: 两类配额齐备且显示占比

- **WHEN** 读取 `[data-screen="budget"]` 的文本
- **THEN** 同时命中 `评测次数` 与 `Token`，且存在至少一个百分比形式的用量显示

#### Scenario: 不使用 AI 积分口径

- **WHEN** 全文搜索 `AI 积分`
- **THEN** 命中数为 0

#### Scenario: 超额空间被标记

- **WHEN** 查询 `[data-quota-over]`
- **THEN** 至少 1 个元素，且其类名或样式指向 destructive 语义

### Requirement: 风险审计与操作审计分立

`risk` 屏（风险审计）SHALL 面向 Agent 运行时的安全风险：提示注入、敏感信息泄露、越权工具调用等，列表 SHALL 含 `风险类型`、`等级`、`关联会话`、`时间`。

`audit` 屏（操作审计）SHALL 面向平台内的人为操作：SHALL 含 `操作人`、`操作`、`对象`、`结果`、`时间` 五列，并 SHALL 把「改评估器阈值」「改金标准」「重跑任务」三类标记为高风险，提供「仅看高风险」开关。

两者 SHALL 为两个独立的屏，SHALL NOT 合并为同一屏的两个页签。

#### Scenario: 两屏独立存在

- **WHEN** 查询 `.nav-item[data-go="risk"]` 与 `.nav-item[data-go="audit"]`
- **THEN** 各返回 1 个元素

#### Scenario: 高风险筛选生效

- **WHEN** 在 `audit` 屏打开「仅看高风险」开关
- **THEN** 表格可见行数减少，且剩余行均带高风险标记

#### Scenario: 风险审计含风险类型列

- **WHEN** 读取 `[data-screen="risk"]` 的表头
- **THEN** 含 `风险类型` 与 `等级`

### Requirement: 通知中心

`notify` 屏 SHALL 呈现通知列表，SHALL 区分已读与未读，SHALL 提供「全部标为已读」操作。未读数 SHALL 在导航或顶栏以徽标显示。

#### Scenario: 全部标为已读后未读数归零

- **WHEN** 点击「全部标为已读」
- **THEN** 未读徽标元素带 `hidden`，或其文本为 `0`

### Requirement: 总览与快速启动

`dashboard` 屏 SHALL 呈现当前空间的关键指标卡（至少含 评测任务数、平均分、门禁通过率、Token 用量）与趋势图。

`quickstart` 屏 SHALL 以带步骤的引导清单呈现至少三条主线：接入观测数据、创建评估任务、构建评测数据集；每步 SHALL 可点击跳转到对应屏。

#### Scenario: 快速启动的步骤可跳转

- **WHEN** 点击 `quickstart` 屏中带 `[data-go]` 的引导按钮
- **THEN** 对应 `[data-screen]` 不带 `hidden`，且左侧对应导航项带 `.on`

#### Scenario: 总览指标卡齐备

- **WHEN** 查询 `[data-screen="dashboard"] [data-kpi]`
- **THEN** 返回元素数 ≥ 4

### Requirement: 通用表格交互

列表类屏的表格 SHALL 支持排序、筛选与分页，且交互 SHALL 真实生效（改变可见行的顺序、数量或内容），SHALL NOT 为静态装饰。

#### Scenario: 排序改变行顺序

- **WHEN** 点击某表格的 `[data-sort]` 表头两次
- **THEN** 第一次点击后首行内容与初始不同或排序标记翻转；第二次点击后排序方向标记与第一次相反

#### Scenario: 筛选改变可见行数

- **WHEN** 在某列表屏选择一个 `[data-filter]` 选项
- **THEN** 可见数据行数发生变化，且剩余行均匹配该筛选条件

#### Scenario: 分页切换改变当前页

- **WHEN** 点击分页控件的下一页
- **THEN** 当前页码显示递增，且表格内容发生变化

### Requirement: 弹窗的打开与关闭

所有 `[data-dlg]` 触发的弹窗 SHALL 可通过 Escape 键与关闭按钮两种方式关闭。

#### Scenario: Escape 关闭弹窗

- **WHEN** 打开任一弹窗后派发 Escape 键事件
- **THEN** 该弹窗根元素带 `hidden` 属性
