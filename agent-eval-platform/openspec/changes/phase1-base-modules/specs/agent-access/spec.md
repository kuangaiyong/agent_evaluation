## Purpose

管理被测智能体如何把执行轨迹送进平台。接入摩擦是内部平台的第一死因，因此这项能力的目标是让接入降到「加个环境变量」的成本，而不是让每个团队为平台改代码。

## ADDED Requirements

### Requirement: 三条接入通道

系统 SHALL 以 LoongSuite 为统一接入方案，按被测对象的形态提供三条通道，并在界面上说明各自适用范围：

| 通道 | 适用对象 | 形态 |
|---|---|---|
| ① Python Agent | AgentScope 等 Python 智能体应用 | 包裹原启动命令，业务代码零改动 |
| ② Pilot | OpenCode、Hermes Agent 等本地 Coding CLI | 装在开发机上的本地采集器，自动注入插件 |
| ③ OTLP 直推 | CodeBuddy 及未被 Pilot 覆盖的工具 | 工具自身按 OTel 规范推送，或直打自研网关 |

界面 SHALL NOT 再以「AgentScope / OpenCode / HTTP API」作为通道划分——那是按产品名而非按接入形态切分，会让新工具无处归类。

#### Scenario: 按形态选择通道

- **WHEN** 用户进入接入中心
- **THEN** 页面呈现三条通道及各自的适用对象
- **AND** 每条通道给出可直接复制的接入命令与需配置的环境变量名

#### Scenario: 未被 Pilot 覆盖的工具

- **WHEN** 用户要接入的工具不在 Pilot 的官方支持清单内
- **THEN** 界面明确提示该情况，并指引走通道 ③
- **AND** 不把名称相近但实为不同产品的工具标为已支持

### Requirement: 应用接入管理

系统 SHALL 以「应用」为单位管理接入对象，每个应用记录名称、智能体类型、接入通道、API Key、接入状态、模型、累计 Trace 数与平均 Score。

#### Scenario: 应用列表呈现接入口径

- **WHEN** 用户查看已接入应用列表
- **THEN** 列表包含「智能体类型」与「接入通道」两列
- **AND** 接入状态区分已连接、上报中断、待验证三种

#### Scenario: 注册新应用

- **WHEN** 具备写权限的用户提交应用注册表单
- **THEN** 系统创建应用并生成 API Key
- **AND** 界面提示需在智能体侧配置上报地址

#### Scenario: 上报中断可见

- **WHEN** 某应用在约定时长内没有新的 Trace 上报
- **THEN** 该应用状态显示为上报中断并标明已中断时长
- **AND** 仪表盘的告警区同步呈现该异常

### Requirement: 凭据管理

系统 SHALL 支持轮换应用的 API Key，并 SHALL NOT 在列表中完整展示 Key。

#### Scenario: Key 脱敏展示

- **WHEN** 用户查看应用列表
- **THEN** API Key 以脱敏形式展示，仅保留首尾片段

#### Scenario: 轮换 Key

- **WHEN** 具备写权限的用户轮换某应用的 Key
- **THEN** 旧 Key 立即失效，界面提示需更新智能体侧配置
