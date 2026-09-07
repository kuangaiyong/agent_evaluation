## Purpose

定义 `docs/prototype.html` 的外壳契约：20 屏导航结构、屏切换语义、工作空间/角色/主题三个全局切换器。外壳是所有其他屏的载体，它的 DOM 契约同时是 `prototype.smoke.js` 的断言接口。

## ADDED Requirements

### Requirement: 品牌与命名

原型 SHALL 使用品牌名 `TAgenEval`，且 SHALL NOT 在任何可见文本中出现 `AgentLoop`。数据分组的名称 SHALL 为「数据魔方」，SHALL NOT 出现「数据中心」。

原型 SHALL NOT 出现下列阿里云商业服务名称：`SLS`、`日志服务`、`云监控`、`CMS 工作空间`、`MSE`、`ARMS`、`AgentSpace`、`AI 积分`、`aliyuncs.com`。

原型 MAY 出现 `LoongSuite`、`OpenTelemetry`、`OTLP`、`eBPF`，以及被观测方框架名（如 `LangChain`、`AgentScope`、`Claude Code`）—— 它们是接入技术栈与接入对象，不是云服务依赖。

#### Scenario: 全文不含被禁名称

- **WHEN** 对 `docs/prototype.html` 全文做大小写不敏感搜索
- **THEN** `AgentLoop`、`数据中心`、`SLS`、`云监控`、`MSE`、`ARMS`、`AgentSpace`、`aliyuncs.com` 的命中数均为 0

#### Scenario: 保留的技术栈名称存在

- **WHEN** 搜索 `LoongSuite`
- **THEN** 命中数 ≥ 1，且出现在接入中心屏内

### Requirement: 20 屏导航

原型 SHALL 提供 20 个导航项，按 6 个一级分组呈现；一级分组为不可点击的标题，二级项为可点击的屏入口：

| 分组 | 屏 id |
|---|---|
| 总览 | `dashboard`、`quickstart` |
| 观测与接入 | `access`、`traces`、`boards` |
| 评测与实验 | `evaluators`、`tasks`、`insight`、`badcases`、`regression` |
| 数据魔方 | `trajectory`、`datasets`、`pipeline` |
| 持续优化 | `assets`、`memory` |
| 治理与系统 | `risk`、`audit`、`budget`、`space`、`notify` |

每个导航项 SHALL 带 `class="nav-item"` 与 `data-go="<屏 id>"`。另有下钻屏 `trace`（单条链路详情）SHALL 存在于 DOM 但 SHALL NOT 拥有导航项。

#### Scenario: 导航项数量与屏一一对应

- **WHEN** 查询 `.nav-item`
- **THEN** 返回 20 个元素，其 `data-go` 值集合等于上表 20 个屏 id 的集合

#### Scenario: 逐个点击导航，每次只显示一屏

- **WHEN** 依次点击全部 20 个 `.nav-item`
- **THEN** 每次点击后，`[data-screen]` 中不带 `hidden` 属性的元素恰为 1 个，且其 `data-screen` 等于被点项的 `data-go`，且该导航项带 `.on` 类、其余导航项不带 `.on`

#### Scenario: 链路详情屏无导航入口

- **WHEN** 查询 `.nav-item[data-go="trace"]`
- **THEN** 返回 0 个元素；但 `[data-screen="trace"]` 存在于 DOM

### Requirement: 工作空间切换

原型 SHALL 在顶部提供工作空间切换器，至少 3 个演示空间。切换空间 SHALL 更新页面上的当前空间名显示。

#### Scenario: 切换空间后当前空间名随之改变

- **WHEN** 点击空间切换器中的另一个空间项 `[data-space]`
- **THEN** 当前空间名显示元素的文本等于该项的 `data-space` 值，且该项带 `.on` 类

### Requirement: 角色切换与权限可见性

原型 SHALL 提供四种角色的切换：`admin`（管理员）、`devops`（测试开发）、`tester`（测试工程师）、`viewer`（只读）。

需要写权限的元素 SHALL 标注 `data-role-only="<role,...>"`。切换角色时，系统 SHALL 对所有 `[data-role-only]` 元素重算可见性：当前角色在其列表内则移除 `hidden`，否则添加 `hidden`。

#### Scenario: 只读角色看不到任何写操作入口

- **WHEN** 将角色切换为 `viewer`
- **THEN** 所有 `[data-role-only]` 元素中，`data-role-only` 不含 `viewer` 的元素全部带 `hidden` 属性

#### Scenario: 管理员能看到空间设置入口

- **WHEN** 将角色切换为 `admin`
- **THEN** `[data-role-only]` 中 `data-role-only` 含 `admin` 的元素均不带 `hidden` 属性

#### Scenario: 角色切换可逆

- **WHEN** 先切到 `viewer` 再切回 `admin`
- **THEN** 带 `data-role-only="admin"` 的元素恢复为不带 `hidden`

### Requirement: 明暗主题切换

原型 SHALL 提供主题切换控件 `[data-theme-toggle]`。切换 SHALL 通过在根元素设置 `data-theme="light|dark"` 生效，SHALL NOT 依赖逐元素改写内联样式。

#### Scenario: 主题切换改变根元素属性

- **WHEN** 点击 `[data-theme-toggle]`
- **THEN** 文档根元素的 `data-theme` 属性值在 `light` 与 `dark` 之间翻转

### Requirement: 零外部依赖与零网络请求

原型 SHALL NOT 引用除 `fonts.googleapis.com` / `fonts.gstatic.com` 之外的任何外部资源，SHALL NOT 包含 `<script src=...>` 外链，SHALL NOT 在运行时发起 `fetch` 或 `XMLHttpRequest`。

#### Scenario: 无外链脚本

- **WHEN** 查询 `script[src]`
- **THEN** 返回 0 个元素

#### Scenario: 页面脚本执行无运行时错误

- **WHEN** 在 jsdom 中以 `runScripts:'dangerously'` 加载并完成全部交互断言
- **THEN** 捕获到的 `window error` 与 `jsdomError` 累计为 0 条
