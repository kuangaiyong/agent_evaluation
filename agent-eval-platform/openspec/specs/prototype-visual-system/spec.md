# prototype-visual-system Specification

## Purpose
定义原型的视觉体系契约：设计 token、字体、圆角与间距、动效、可访问性与响应式。这些规则决定原型「像不像一个成熟 SaaS 产品」，也是它能被部门直接拿去推广的前提。来源为 `ui-ux-pro-max` 的 `AI-Native UI` 风格与其 Pre-Delivery Checklist。

## Requirements

### Requirement: 设计 token 单一来源

所有颜色 SHALL 以 CSS 自定义属性定义在 `:root`，组件内 SHALL NOT 出现硬编码的十六进制颜色值（`#RRGGBB` / `#RGB`）或 `rgb()` 字面量。暗色主题 SHALL 只重定义 token，SHALL NOT 重写组件规则。

明色 token 取值 SHALL 为：`--color-primary:#7C3AED`、`--color-on-primary:#FFFFFF`、`--color-secondary:#A78BFA`、`--color-accent:#0891B2`、`--color-background:#FAF5FF`、`--color-foreground:#1E1B4B`、`--color-card:#FFFFFF`、`--color-muted:#ECEEF9`、`--color-muted-foreground:#475569`、`--color-border:#DDD6FE`、`--color-destructive:#DC2626`、`--color-ring:#7C3AED`。

#### Scenario: 组件规则内无硬编码颜色

- **WHEN** 提取 `<style>` 内除 `:root` 与 `[data-theme="dark"]` 之外的全部规则块
- **THEN** 其中匹配 `#[0-9a-fA-F]{3,8}\b` 的次数为 0

#### Scenario: 暗色只覆写 token

- **WHEN** 提取 `[data-theme="dark"]` 选择器下的声明
- **THEN** 全部声明的属性名均以 `--` 开头

### Requirement: 字体

原型 SHALL 使用 `Space Grotesk` 作为标题与数字字体、`DM Sans` 作为正文字体，二者经单条 Google Fonts `<link>` 引入。等宽内容 SHALL 使用系统等宽栈，SHALL NOT 引入第三个网络字体。

#### Scenario: 字体只请求一次且只含两族

- **WHEN** 查询 `link[href*="fonts.googleapis.com"]`
- **THEN** 返回 1 个元素，其 `href` 同时包含 `DM+Sans` 与 `Space+Grotesk`，且不含其他 `family=` 项

### Requirement: 图标使用 SVG 而非 emoji

所有功能性图标 SHALL 为内联 `<svg>`。原型 SHALL NOT 使用 emoji 承担图标语义。

#### Scenario: 导航项图标为 SVG

- **WHEN** 检查每个 `.nav-item`
- **THEN** 每个导航项内至少包含 1 个 `<svg>` 元素

#### Scenario: 全文无 emoji 图标

- **WHEN** 对全文匹配常见 emoji 码点区间（`\u{1F300}-\u{1FAFF}`、`\u{2600}-\u{27BF}`）
- **THEN** 命中数为 0

### Requirement: 可访问性

原型 SHALL 满足：可点元素带 `cursor: pointer`；焦点态可见（SHALL NOT 出现无替代样式的 `outline: none`）；图标按钮带 `aria-label`；表格有 `<th>` 表头。

#### Scenario: 无裸 outline:none

- **WHEN** 在 `<style>` 中搜索 `outline:none` / `outline: none`
- **THEN** 每处命中所在的规则块内必须同时出现 `box-shadow` 或 `outline-offset` 或 `border-color` 作为焦点替代；否则判定失败

#### Scenario: 图标按钮有可访问名称

- **WHEN** 查询只含 `<svg>` 而无文本内容的 `button`
- **THEN** 每个此类按钮均带非空 `aria-label` 属性

### Requirement: 动效与 reduced-motion

过渡时长 SHALL 在 150-400ms 之间，SHALL 只对 `opacity` 与 `transform` 做动画。原型 SHALL 包含 `prefers-reduced-motion: reduce` 媒体查询并在其中将动画与过渡时长归零。

#### Scenario: 存在 reduced-motion 兜底

- **WHEN** 在 `<style>` 中搜索 `prefers-reduced-motion`
- **THEN** 命中数 ≥ 1，且其规则块内包含 `animation-duration` 与 `transition-duration` 的归零声明

### Requirement: 响应式与表格溢出

页面在 375 / 768 / 1024 / 1440 四个宽度下 SHALL NOT 产生横向滚动。宽表格 SHALL 由带 `overflow-x: auto` 的容器包裹 —— 容器内部横滚是允许的，页面 `body` 横滚不允许。

#### Scenario: 每个表格都有滚动容器

- **WHEN** 查询所有 `<table>`
- **THEN** 每个表格的某个祖先元素带有 `.table-wrap` 类（该类在样式中声明 `overflow-x: auto`）

### Requirement: 图表可访问性

图表 SHALL 为内联 SVG。多系列图表 SHALL NOT 仅靠色相区分系列，SHALL 叠加线型或点形状差异，并提供直接的系列标注。每张图表 SHALL 提供可展开的数据表 fallback。

#### Scenario: 多系列折线图带线型区分

- **WHEN** 查询带 `data-chart="line-multi"` 的 SVG
- **THEN** 其内部的 `path` 元素中至少有一个带 `stroke-dasharray` 属性

#### Scenario: 每张图表有数据表 fallback

- **WHEN** 查询所有 `[data-chart]`
- **THEN** 每个图表元素的容器内均存在一个 `[data-chart-table]` 元素
