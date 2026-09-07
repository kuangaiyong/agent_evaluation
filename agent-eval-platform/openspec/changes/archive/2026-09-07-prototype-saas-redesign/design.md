# 设计：TAgenEval 原型重做

## 1. 交付形态

**选了什么** — 单个 `docs/prototype.html`，无构建、无外部 JS 框架，只引 Google Fonts 一条 `<link>`；全部 CSS/JS 内联。

**为什么** — ① 现有原型与 `prototype.smoke.js` 的 jsdom 断言依赖「读一个 HTML 文件、`runScripts:'dangerously'` 执行」这个前提，拆多文件会让测试基础设施整个重写；② 原型要能双击打开、能丢给部门任何人看，不能要求装 node_modules；③ 项目 CLAUDE.md 定它是「界面的事实来源」，单文件才好做 diff 审阅。

**错了的代价** — 文件会到 5000～7000 行，单文件编辑成本高、多人协作会冲突。若后期要拆，拆分点是「每屏一个 `<template>` + 一个 loader」，届时 smoke 测试需同步改造。这个代价可接受，因为原型不是长期演进的生产代码。

## 2. 视觉体系（来源：`ui-ux-pro-max` 查询结果）

查询：`"internal AI evaluation platform dashboard SaaS" --design-system --variance 4 --motion 3 --density 8`
命中风格 **AI-Native UI**（明暗双支持，accessibility risk: low）。

> ⚠️ 该查询同时返回了 pattern「Product Demo + Features」，那是**营销落地页**结构（Hero → 视频 → 功能分栏 → CTA），与控制台不符，**已弃用**。仅采纳其 style / colors / typography / motion / checklist 部分。这是 skill 文档要求的「verify fit before applying」。

### 2.1 色板（明色，直接取 skill 输出）

| Token | 值 | 用途 |
|---|---|---|
| `--color-primary` | `#7C3AED` | 主色，主按钮、选中态、链接 |
| `--color-on-primary` | `#FFFFFF` | 主色上的文字 |
| `--color-secondary` | `#A78BFA` | 次强调、图表第二系列 |
| `--color-accent` | `#0891B2` | CTA/高亮（skill 已从 `#06B6D4` 调深以满足对比度） |
| `--color-on-accent` | `#000000` | accent 上的文字 |
| `--color-background` | `#FAF5FF` | 页面底 |
| `--color-foreground` | `#1E1B4B` | 主文字 |
| `--color-card` / `--color-card-foreground` | `#FFFFFF` / `#1E1B4B` | 卡片 |
| `--color-muted` / `--color-muted-foreground` | `#ECEEF9` / `#475569` | 次级背景 / 次级文字 |
| `--color-border` | `#DDD6FE` | 描边、分隔线 |
| `--color-destructive` / `--color-on-destructive` | `#DC2626` / `#FFFFFF` | 失败、删除、超阈 |
| `--color-ring` | `#7C3AED` | 焦点环 |

**语义状态色**（原型自定义，参考页同款语义）：`--st-pass #16A34A` / `--st-warn #D97706` / `--st-fail #DC2626` / `--st-running #0891B2` / `--st-idle #64748B`。

**暗色**：skill 只声明「Dark supported」未给具体值，由本设计推导 —— 背景 `#0F0D1F`、卡片 `#181530`、前景 `#EDE9FE`、边框 `#2E2A47`、muted `#221E3D` / muted-fg `#A5A0C4`，主色在暗色下提亮为 `#9F7AEA` 以保住 4.5:1。**每个色只在 `:root` 定义一次，暗色仅重定义 token，不写死颜色在组件里。**

**错了的代价** — 色板是全局 token，改一次全站生效，代价低。这是可以事后调的决策。

### 2.2 字体

`Space Grotesk`（标题/数字）+ `DM Sans`（正文），skill 给出的配对，且 DM Sans 正是用户参考页所用。等宽用系统 `ui-monospace, SFMono-Regular, Menlo, monospace`（Trace ID、Builtin ID、代码片段），不额外引第三种字体以省一次网络请求。

### 2.3 密度与间距

density 8/10（Dense/Dashboard）：间距阶 `4 / 8 / 12 / 16 / 24 / 32`，卡片内边距 16-20px，表格行高 44px（同时满足触控 44×44 的最小命中区）。圆角 `--radius: 12px`（卡片/弹窗 16px，按钮/输入 10px，徽章胶囊 999px）。阴影仅两级：`--sh-1`（卡片，极轻）、`--sh-2`（弹窗/下拉）。

### 2.4 动效

motion 3/10（Subtle）：过渡 **200-300ms**、`ease-out`；只动 `opacity` 与 `transform`，不动 `width/height`。**必须包 `@media (prefers-reduced-motion: reduce)` 把动画时长归零。** 不引 GSAP（skill 给的是 GSAP 片段，但本原型无外部 JS 依赖这条优先）。

### 2.5 强制约束（来自 skill 的 Pre-Delivery Checklist）

- **图标一律内联 SVG（Lucide 风格线性图标），禁止 emoji 当图标**
- 所有可点元素 `cursor: pointer`，hover 有 150-300ms 过渡
- 文本对比度 ≥ 4.5:1（明暗两套都要）
- 焦点态可见，**不许 `outline: none` 而不给替代**
- 响应式断点 375 / 768 / 1024 / 1440，表格用 `overflow-x: auto` 包裹，页面本身不横向滚动

## 3. 图表方案

**选了什么** — 全部手写内联 SVG，不引图表库。四种图形，按 skill 的 `--domain chart` 建议选型：

| 场景 | 图表 | 依据 |
|---|---|---|
| 评分趋势、Token 趋势 | **折线图** | Trend Over Time；<1000 点用 SVG |
| **分数 vs 门禁阈值 τ=0.75** | **Bullet Chart** | Performance vs Target (Compact)，为 KPI-vs-阈值 而生 |
| 评估器多维对比（A/B 版本） | **雷达图** | Multi-Variable Comparison，限 2-3 数据集、5-8 轴 |
| 分数分布 | **直方图/条形** | 离散分桶 |

**a11y 硬约束（skill 明确要求）**：多系列**不能只靠色相区分**，必须叠加线型（实线/虚线/点线）或点形状 + 直接标注系列名；每张图旁提供可展开的**数据表 fallback**。

**为什么不引 Chart.js** — 单文件无构建、离线可开、jsdom 里不能跑 canvas。手写 SVG 在 jsdom 里可被断言。

**错了的代价** — 手写 SVG 做交互（hover tooltip、缩放）成本高，本原型只做 hover 高亮 + tooltip，不做缩放。若后续要复杂图表交互，需换库并放弃单文件形态。

## 4. DOM 契约（供 smoke 测试断言）

沿用现有原型的 `data-*` 约定并扩展，**这是测试与实现之间的接口**：

| 属性 | 含义 |
|---|---|
| `[data-screen="<id>"]` | 一屏容器；非当前屏带 `hidden` 属性 |
| `.nav-item[data-go="<id>"]` | 左侧导航项；当前项带 `.on` |
| `[data-tab="<group>"][data-tv="<value>"]` | 页内页签；当前项带 `.on` |
| `[data-dlg="<id>"]` | 点击打开 id 弹窗；弹窗根 `#<id>`，关闭态带 `hidden` |
| `[data-step]` / `[data-stepgo]` | 弹窗内分步表单的步骤面板与前进/后退 |
| `[data-drill="<screen>:<key>"]` | 表格行下钻，跳到目标屏并定位 |
| `[data-space]` / `[data-role]` / `[data-theme-toggle]` | 空间切换 / 角色切换 / 主题切换 |
| `[data-role-only="<role,...>"]` | 仅指定角色可见的元素（角色切换时增删 `hidden`） |
| `[data-sort="<col>"]` / `[data-filter="<group>"]` / `[data-page]` | 排序 / 筛选 / 分页 |

**错了的代价** — 契约定错会让 smoke 测试大面积重写。因此**先写测试（Task 11 的断言在各任务中同步落地），再写实现**，契约以测试为准。

## 5. 信息架构：20 屏 + 1 下钻屏

| 分组 | 屏 id | 说明 |
|---|---|---|
| 总览 | `dashboard` `quickstart` | 工作台、快速启动 |
| 观测与接入 | `access` `traces` `boards` | 接入中心、链路观测、仪表盘 |
| 评测与实验 | `evaluators` `tasks` `insight` `badcases` `regression` | 评估器、评估任务、分析洞察、Bad Case、实验与回归 |
| 数据魔方 | `trajectory` `datasets` `pipeline` | 轨迹库、数据集、数据加工 |
| 持续优化 | `assets` `memory` | Agent 资产、经验与记忆 |
| 治理与系统 | `risk` `audit` `budget` `space` `notify` | 风险审计、操作审计、成本与配额、空间与成员、通知中心 |

另有下钻页 `trace`（单条链路详情），由 `traces` 行下钻进入，**不占导航项**。导航项共 20 个，`[data-screen]` 容器合计 21 个。

## 6. 评估器：DeepEval 映射

**选了什么** — 评估器屏分「预置（DeepEval）」与「自定义」两类。预置清单照搬 DeepEval 官方类名（经 Context7 核实），配置表单字段用其真实参数。

**打分公式三分量的映射（本设计提出，标为待确认）**：

| 分量 | 建议来源 | 说明 |
|---|---|---|
| `s_safety`（0/1 乘法门控） | `ToxicityMetric` / `BiasMetric` 任一超标即 0 | 与既有「安全违规不能被高完成度抵消」一致 |
| `s_completion` | `TaskCompletionMetric`（多轮场景用 `ConversationCompletenessMetric`） | 主完成度 |
| `s_robustness` | `ToolCorrectnessMetric` + `ArgumentCorrectnessMetric` 加权，叠加 k 次试次的一致性 | 过程稳健性 |

**为什么这么映射** — 三分量原本就是「安全门控 / 完成度 / 稳健性」，DeepEval 的 agentic 指标恰好一一对应。

**错了的代价** — 映射错会让分数含义偏移，但**原型层面只是展示文案与示意数值，不产生真实评分**，改动成本仅是改几处静态文本。真正落地前需用户确认。**原型中该映射会显式标注「待确认」徽标**，避免被当成既定口径。

**阈值** — DeepEval `threshold` 默认 0.5，我们统一取 **τ=0.75**；原型表单默认值填 0.75 并在旁注明「平台口径 τ=0.75，非 DeepEval 默认 0.5」。

## 7. 规模模型（1000 人）

**选了什么** — 三件套：顶部**空间切换器**（下拉，3 个演示空间）、右上**角色切换器**（管理员 / 测试开发 / 测试工程师 / 只读）、空间级**配额**（评测次数 + Token 用量，超额阻断）。

角色用 `[data-role-only]` 声明式控制可见性，切换角色时统一增删 `hidden`。四角色权限：

| 能力 | 管理员 | 测试开发 | 测试工程师 | 只读 |
|---|---|---|---|---|
| 查看全部 | ✓ | ✓ | ✓ | ✓ |
| 建/改评估任务、数据集 | ✓ | ✓ | ✓ | — |
| 建/改评估器、Pipeline、Agent 资产 | ✓ | ✓ | — | — |
| 空间设置、成员、配额 | ✓ | — | — | — |

**错了的代价** — 权限矩阵若与部门实际不符，改的是一张表 + 若干 `data-role-only` 值，成本低。但**导航是否按空间隔离**这条如果错了，影响信息架构，需重做外壳。

## 8. 与已实现代码的关系

本次**只改原型，不动 `backend/` 与 `frontend/`**。已知会产生的偏差在交付报告列清单，包括但不限于：`metric-dictionary` 能力域与 `/metrics` 页失去依据、`scripts/sync_metrics.py` 失效、导航项 14 → 20、删除指标字典屏、新增空间/角色/配额模型。**不在本次修复。**

## 9. 不做的事

- 不引任何外部 JS 库（含 Tailwind CDN、Chart.js、GSAP）
- 不做营销落地页
- 不发网络请求，演示数据静态内置
- 不改外层方法论文档
- 不实现 DeepEval 真实集成
