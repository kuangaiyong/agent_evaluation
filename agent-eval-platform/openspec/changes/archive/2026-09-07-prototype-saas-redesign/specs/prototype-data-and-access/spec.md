## Purpose

定义数据入口与数据加工两条主线的契约：接入中心（LoongSuite 四通道）、链路观测、数据魔方三屏（轨迹库 / 数据集 / 数据加工）。这条线决定「评测的数据从哪来、怎么变成可复用的评测集」。

## ADDED Requirements

### Requirement: 接入中心提供 LoongSuite 四通道

`access` 屏 SHALL 按被接入对象的形态提供四条接入通道，每条 SHALL 标明技术、适用对象与侵入性：

| 通道 | 技术 | 适用对象 |
|---|---|---|
| Python Agent | LoongSuite Python 探针 | LangChain / LangGraph / AgentScope / OpenAI SDK 等应用内 Agent |
| Pilot | LoongSuite Pilot 本地采集客户端 | Claude Code / Codex / OpenCode / Cursor 等本地 Coding Agent |
| OTLP 直推 | OpenTelemetry SDK | 自研 Agent、无探针覆盖的框架 |
| eBPF 无侵入 | 主机/容器级内核态采集 | 改不了启动方式的存量服务 |

四条通道的上报端点 SHALL 指向自建 OTLP 采集网关，SHALL NOT 出现任何 `*.aliyuncs.com` 域名或 `LicenseKey` 字样。鉴权 SHALL 表述为「接入 Token」。

#### Scenario: 四通道齐备且可切换

- **WHEN** 点击 `access` 屏内 `[data-tab="channel"]` 的四个页签
- **THEN** 每次点击后被选中项带 `.on`，且对应的接入指引面板不带 `hidden`、其余三个带 `hidden`

#### Scenario: 上报端点不指向云厂商

- **WHEN** 读取 `[data-screen="access"]` 的文本
- **THEN** `aliyuncs.com` 与 `LicenseKey` 命中数均为 0，且 `OTLP` 命中数 ≥ 1

#### Scenario: eBPF 通道标注为零改动

- **WHEN** 切换到 eBPF 通道页签
- **THEN** 该面板文本同时包含 `eBPF` 与 `无侵入`（或 `零改动`）

### Requirement: 应用列表带接入通道列

`access` 屏的应用列表 SHALL 含「接入通道」列，允许同一空间内多通道混用。

#### Scenario: 列表含接入通道列且取值来自四通道

- **WHEN** 读取应用列表表头与数据行
- **THEN** 表头含 `接入通道`；该列出现的取值均属于 `Python Agent` / `Pilot` / `OTLP 直推` / `eBPF` 四者之一

### Requirement: 链路观测的多视角与下钻

`traces` 屏 SHALL 提供至少三个视角页签：`Trace 列表`、`会话分析`、`Token 与成本`。Trace 列表 SHALL 含列：`Trace ID`、`输入`、`输出`、`耗时`、`Total tokens`、`入口应用`、`会话 ID`。

行 SHALL 可下钻到 `trace` 屏；`trace` 屏 SHALL 呈现 span 树与逐步耗时。

#### Scenario: Trace 行下钻到详情

- **WHEN** 点击 `traces` 屏中带 `[data-drill^="trace:"]` 的行
- **THEN** `[data-screen="trace"]` 不带 `hidden`，且详情标题文本包含被点行的 Trace ID

#### Scenario: 详情页可返回列表

- **WHEN** 在 `trace` 屏点击返回控件 `[data-back]`
- **THEN** `[data-screen="traces"]` 不带 `hidden`，`[data-screen="trace"]` 带 `hidden`

### Requirement: 数据魔方三屏

数据分组 SHALL 命名为「数据魔方」，含三屏：`trajectory`（轨迹库）、`datasets`（数据集）、`pipeline`（数据加工）。

轨迹库 SHALL 标明数据源为 `Trace` 与 `eBPF 日志` 两路，列表 SHALL 含 `Steps`、`模型调用`、`工具调用`、`Tokens`、`耗时` 列。

#### Scenario: 数据魔方分组含三个导航项

- **WHEN** 查询「数据魔方」分组下的 `.nav-item`
- **THEN** 返回 3 个元素，`data-go` 分别为 `trajectory`、`datasets`、`pipeline`

#### Scenario: 轨迹库标明双数据源

- **WHEN** 读取 `[data-screen="trajectory"]` 的文本
- **THEN** 同时命中 `Trace` 与 `eBPF`

### Requirement: 数据集支持四种创建来源

创建数据集弹窗 SHALL 提供四种来源：`从轨迹加工`、`从链路提取`、`上传文件`（CSV / Excel / JSONL）、`从空白开始`。

数据集详情 SHALL 含字段 `id`、`input`、`output`、`expected_output`、`trajectory`，并提供「发起评估」与「发起实验」两个操作入口。

#### Scenario: 四种来源齐备

- **WHEN** 打开创建数据集弹窗
- **THEN** 四种来源选项均存在且可点选，点选后带 `.on`

#### Scenario: 数据集详情可直接发起评估

- **WHEN** 在数据集详情点击「发起评估」
- **THEN** `[data-screen="tasks"]` 不带 `hidden`，且新建任务弹窗为打开状态

### Requirement: 数据加工 Pipeline

`pipeline` 屏 SHALL 呈现「输入 → 算子 → 输出数据集」的流水线结构，SHALL 支持单次执行与周期执行两种调度模式，SHALL 提供至少一个内置处理模版（如 QA 问答对提取）。

#### Scenario: 流水线三段结构可见

- **WHEN** 读取 `[data-screen="pipeline"]` 的文本
- **THEN** 同时命中 `输入`、`算子`（或 `处理`）、`输出`

#### Scenario: 两种调度模式可选

- **WHEN** 打开创建 Pipeline 弹窗
- **THEN** `单次执行` 与 `周期执行` 两个选项均存在
