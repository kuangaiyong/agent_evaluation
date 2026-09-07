# 任务拆解

## 全局约定

- **所有任务改同一个文件 `docs/prototype.html`**，因此任务必须串行，不可并行派工。
- 测试统一写进 `docs/prototype.smoke.js`（整体重写）。该文件是顺序执行的 node 脚本，非测试框架：每个任务在文件末尾追加自己的断言段落，末尾统一汇总。
- 跑法：`cd agent-eval-platform/docs && node prototype.smoke.js`
- **基线**：改动前 `prototype.smoke.js` 实测 **62 / 62 通过，退出码 0**（注：项目 CLAUDE.md 记载的「28 项」是过时数字，以实测为准，交付时更正）。
- **验收判定与「判不了」分离**：某任务验收若出现**非本任务目标**的失败（例如 jsdom 自身报 `Not implemented: HTMLCanvasElement`），判为「判不了」并点名是什么失败，不计入该任务的通过/不通过。

---

## Task 1: 设计 token、外壳骨架与 20 屏导航

**Files:**
- Create: `docs/prototype.html`（整体重写，覆盖旧文件）
- Create: `docs/prototype.smoke.js`（整体重写）
- Test: `docs/prototype.smoke.js`

**Depends on:** 无

**Interfaces（本任务产出，后续任务消费）:**
- `[data-screen="<id>"]`，非当前屏带 `hidden`
- `.nav-item[data-go="<id>"]`，当前项带 `.on`
- CSS 变量：`--color-primary` 等 12 个 token 定义于 `:root`，暗色在 `[data-theme="dark"]` 下只覆写 token
- 全局函数 `go(screenId)` 供其他屏内按钮复用

- [x] Step 1: 写会失败的测试

```js
/* TAgenEval 原型交互冒烟测试
 *   cd agent-eval-platform/docs && npm i jsdom && node prototype.smoke.js
 * 静态 grep 只能证明属性写对了，证明不了「点得动」。本文件用 jsdom 真正执行页面
 * 脚本并模拟交互。改原型后必须跑通再提交。 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync("prototype.html", "utf8");
const dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true });
const { window } = dom;
const doc = window.document;
const $ = (s) => doc.querySelector(s);
const $$ = (s) => [...doc.querySelectorAll(s)];
const click = (el) => el && el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
const esc = () => doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
const shown = () => $$("[data-screen]").filter((x) => !x.hasAttribute("hidden"));
const txt = (sel) => ($(sel) ? $(sel).textContent.replace(/\s+/g, " ") : "");

let pass = 0, fail = 0;
const ok = (cond, msg) => { cond ? (pass++, console.log("  ✓ " + msg)) : (fail++, console.log("  ✗ " + msg)); };

/* 错误监听必须在任何交互之前挂上：挂在文件末尾等于一条都没测到 */
const errs = [];
window.addEventListener("error", (e) => errs.push(e.message));
dom.virtualConsole.on("jsdomError", (e) => errs.push(String((e && e.message) || e)));

const SCREENS = ["dashboard","quickstart","access","traces","boards","evaluators","tasks",
  "insight","badcases","regression","trajectory","datasets","pipeline","assets","memory",
  "risk","audit","budget","space","notify"];

console.log("\n【1】品牌与禁用词");
// 挡的真实故障：改名不彻底，交付物里还留着调研对象的品牌或阿里云服务名
const BANNED = ["AgentLoop","数据中心","SLS","云监控","MSE","ARMS","AgentSpace","aliyuncs.com","AI 积分"];
BANNED.forEach((w) => {
  const n = (html.match(new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi")) || []).length;
  ok(n === 0, `禁用词「${w}」命中 ${n}`);
});
ok(/TAgenEval/.test(html), "品牌名 TAgenEval 存在");
ok(/数据魔方/.test(html), "「数据魔方」存在");

console.log("\n【2】20 屏导航");
// 挡的真实故障：导航项与屏容器对不上，点了没反应或一次显示两屏
const navs = $$(".nav-item");
ok(navs.length === 20, `导航项 ${navs.length} 个（期望 20）`);
const gos = navs.map((b) => b.getAttribute("data-go")).sort();
ok(JSON.stringify(gos) === JSON.stringify([...SCREENS].sort()), "导航 data-go 集合与 20 屏一致");
let navOk = 0;
navs.forEach((b) => {
  click(b);
  const t = b.getAttribute("data-go");
  const vis = shown();
  if (vis.length === 1 && vis[0].getAttribute("data-screen") === t &&
      b.classList.contains("on") && $$(".nav-item.on").length === 1) navOk++;
});
ok(navOk === 20, `逐个点击后只显示对应的那一屏（${navOk}/20）`);
ok($$('.nav-item[data-go="trace"]').length === 0 && $('[data-screen="trace"]') !== null,
   "链路详情屏存在于 DOM 但无导航入口");

console.log("\n【3】设计 token 与暗色");
// 挡的真实故障：组件里散落硬编码颜色，换主题时改不动
const styleText = $$("style").map((s) => s.textContent).join("\n");
const rootBlocks = styleText.match(/:root\s*\{[^}]*\}/g) || [];
const darkBlocks = styleText.match(/\[data-theme=["']?dark["']?\]\s*\{[^}]*\}/g) || [];
ok(rootBlocks.length >= 1, ":root 中定义了 token");
["--color-primary","--color-background","--color-foreground","--color-card",
 "--color-border","--color-muted","--color-destructive","--color-ring"].forEach((v) => {
  ok(rootBlocks.join("").includes(v), `token ${v} 已定义`);
});
const nonToken = styleText.replace(/:root\s*\{[^}]*\}/g, "").replace(/\[data-theme=["']?dark["']?\]\s*\{[^}]*\}/g, "");
const hardHex = (nonToken.match(/#[0-9a-fA-F]{3,8}\b/g) || []);
ok(hardHex.length === 0, `组件规则内硬编码颜色 ${hardHex.length} 处（期望 0）${hardHex.slice(0,3).join(",")}`);
ok(darkBlocks.length >= 1 && darkBlocks.join("").split(";").filter((d) => d.trim())
     .every((d) => d.trim().startsWith("--")), "暗色块内只覆写 token");

console.log("\n【4】字体与外链");
ok($$('script[src]').length === 0, "无外链脚本");
const fontLinks = $$('link[href*="fonts.googleapis.com"]');
ok(fontLinks.length === 1, `Google Fonts link ${fontLinks.length} 条（期望 1）`);
ok(fontLinks.length === 1 && /DM\+Sans/.test(fontLinks[0].href) &&
   /Space\+Grotesk/.test(fontLinks[0].href), "字体为 DM Sans + Space Grotesk");
```

- [x] Step 2: 跑 `node prototype.smoke.js`，确认它真的红（此时 `prototype.html` 尚未重写，禁用词与导航断言必然失败）
- [x] Step 3: 实现（**要点与约束，不写代码**）
  - 单文件结构：`<style>` 内联全部 CSS → 外壳 DOM（顶栏 / 侧栏 / 主区）→ 19 个 `[data-screen]` 容器 + `trace` 下钻屏 → `<script>` 内联全部 JS
  - token 全部定义在 `:root`，暗色仅在 `[data-theme="dark"]` 覆写；**组件规则一律用 `var(--x)`，禁止写死颜色**
  - 侧栏按 6 个分组渲染，分组标题不可点击；每个导航项含内联 SVG 图标 + 文字
  - `go(id)` 负责：给所有屏加 `hidden`、给目标屏去 `hidden`、同步 `.nav-item.on`
  - 圆角/间距/阴影按 design.md §2.3 的 token 化取值
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 在某个组件规则里临时写死一个 `#fff`，确认「硬编码颜色 0 处」断言转红；还原

**验收：** `cd agent-eval-platform/docs && node prototype.smoke.js` → 本段断言 **0 FAIL**，累计 PASS ≥ 25，退出码 0

---

## Task 2: 空间/角色/主题三切换器与通用交互基础设施

**Files:** Modify: `docs/prototype.html`；Modify: `docs/prototype.smoke.js`

**Depends on:** Task 1

**Interfaces:** `[data-space]`、`[data-role]`、`[data-theme-toggle]`、`[data-role-only]`、`[data-dlg]`、`[data-sort]`、`[data-filter]`、`[data-page]`；全局函数 `applyRole(role)`、`openDlg(id)`、`closeDlg()`

- [x] Step 1: 写会失败的测试

```js
console.log("\n【5】工作空间切换");
// 挡的真实故障：切了空间但页面上的当前空间名没跟着变，用户以为没切成功
const spaces = $$("[data-space]");
ok(spaces.length >= 3, `演示空间 ${spaces.length} 个（期望 ≥3）`);
const target = spaces[1];
click(target);
ok(txt("[data-space-current]").includes(target.getAttribute("data-space")),
   `切换后当前空间名为 ${target.getAttribute("data-space")}`);
ok(target.classList.contains("on"), "被选空间带 .on");

console.log("\n【6】角色权限可见性");
// 挡的真实故障：切成只读角色后写操作按钮还在，点了才发现没权限
const roleBtn = (r) => $$("[data-role]").find((b) => b.getAttribute("data-role") === r);
const guarded = $$("[data-role-only]");
ok(guarded.length >= 8, `受角色管控的元素 ${guarded.length} 个（期望 ≥8）`);
click(roleBtn("viewer"));
const leak = guarded.filter((el) => !el.getAttribute("data-role-only").split(",").map(s=>s.trim()).includes("viewer")
                                 && !el.hasAttribute("hidden"));
ok(leak.length === 0, `只读角色下泄漏的写操作入口 ${leak.length} 个（期望 0）`);
click(roleBtn("admin"));
const adminOnly = guarded.filter((el) => el.getAttribute("data-role-only").split(",").map(s=>s.trim()).includes("admin"));
ok(adminOnly.every((el) => !el.hasAttribute("hidden")), "管理员下 admin 专属入口全部可见（角色切换可逆）");

console.log("\n【7】主题切换");
// 挡的真实故障：主题靠逐元素改内联样式，切一次漏一片
const rootEl = doc.documentElement;
const before = rootEl.getAttribute("data-theme") || "light";
click($("[data-theme-toggle]"));
const after = rootEl.getAttribute("data-theme");
ok(after !== before && ["light","dark"].includes(after), `主题 ${before} → ${after}`);
click($("[data-theme-toggle]"));
ok(rootEl.getAttribute("data-theme") === before, "再点一次切回原主题");

console.log("\n【8】弹窗开关");
// 挡的真实故障：弹窗只能靠按钮关，Esc 无效，键盘用户被困住
const dlgTriggers = $$("[data-dlg]");
ok(dlgTriggers.length >= 5, `弹窗触发器 ${dlgTriggers.length} 个（期望 ≥5）`);
let escOk = 0, closeOk = 0;
dlgTriggers.forEach((t) => {
  const id = t.getAttribute("data-dlg");
  const dlg = doc.getElementById(id);
  if (!dlg) return;
  click(t);
  const opened = !dlg.hasAttribute("hidden");
  esc();
  if (opened && dlg.hasAttribute("hidden")) escOk++;
  click(t);
  const x = dlg.querySelector("[data-dlg-close]");
  if (x) { click(x); if (dlg.hasAttribute("hidden")) closeOk++; }
  esc();
});
ok(escOk === dlgTriggers.length, `Esc 能关闭全部弹窗（${escOk}/${dlgTriggers.length}）`);
ok(closeOk === dlgTriggers.length, `关闭按钮能关闭全部弹窗（${closeOk}/${dlgTriggers.length}）`);
```

- [x] Step 2: 跑，确认红
- [x] Step 3: 实现要点
  - 空间切换器放顶栏左侧，下拉 3 个演示空间；切换只改 `[data-space-current]` 文本与 `.on`，**不重载数据**（原型层面）
  - `applyRole(role)` 遍历 `[data-role-only]`，按逗号分隔列表决定增删 `hidden`；页面初始化时调一次
  - 主题：只在 `documentElement` 上设 `data-theme`
  - 弹窗：统一 `openDlg/closeDlg`，Escape 监听挂在 `document` 上，每个弹窗内放一个 `[data-dlg-close]`
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 临时去掉 Escape 监听，确认 Esc 断言转红；还原

**验收：** 本段 **0 FAIL**，累计 PASS ≥ 37

---

## Task 3: 接入中心四通道

**Files:** Modify: `docs/prototype.html`、`docs/prototype.smoke.js`
**Depends on:** Task 2
**Interfaces:** `[data-tab="channel"][data-tv="py|pilot|otlp|ebpf"]`、`#acTable`

- [x] Step 1: 写会失败的测试

```js
console.log("\n【9】接入中心四通道");
// 挡的真实故障：接入指引写着云厂商端点或 LicenseKey，照着做接不通我们自建的网关
click($('.nav-item[data-go="access"]'));
const chTabs = $$('[data-tab="channel"]');
ok(chTabs.length === 4, `接入通道页签 ${chTabs.length} 个（期望 4）`);
ok(JSON.stringify(chTabs.map(t=>t.getAttribute("data-tv")).sort()) ===
   JSON.stringify(["ebpf","otlp","pilot","py"]), "四通道标识齐备");
let chOk = 0;
chTabs.forEach((t) => {
  click(t);
  const v = t.getAttribute("data-tv");
  const panes = $$("[data-chpane]");
  const vis = panes.filter((p) => !p.hasAttribute("hidden"));
  if (vis.length === 1 && vis[0].getAttribute("data-chpane") === v && t.classList.contains("on")) chOk++;
});
ok(chOk === 4, `切换通道只显示对应指引（${chOk}/4）`);
const accessTxt = txt('[data-screen="access"]');
ok(/LoongSuite/.test(accessTxt), "接入中心提到 LoongSuite");
ok(/OTLP/.test(accessTxt), "接入中心提到 OTLP");
ok(!/LicenseKey/i.test(accessTxt), "不出现 LicenseKey");
click(chTabs.find((t) => t.getAttribute("data-tv") === "ebpf"));
const ebpfTxt = txt('[data-chpane="ebpf"]');
ok(/eBPF/.test(ebpfTxt) && /(无侵入|零改动)/.test(ebpfTxt), "eBPF 通道标注无侵入/零改动");
const heads = $$("#acTable thead th").map((th) => th.textContent.trim());
ok(heads.includes("接入通道"), `应用列表含「接入通道」列：${heads.join("/")}`);
const chVals = [...new Set($$("#acTable tbody tr").map((tr) =>
  (tr.querySelector("[data-col='channel']") || {}).textContent || "").map((s) => s.trim()).filter(Boolean))];
ok(chVals.length > 0 && chVals.every((v) => ["Python Agent","Pilot","OTLP 直推","eBPF"].includes(v)),
   `接入通道取值合法：${chVals.join("/")}`);
```

- [x] Step 2: 跑，确认红
- [x] Step 3: 实现要点：四个通道页签 + 四个 `[data-chpane]` 指引面板；每个面板给出安装命令、环境变量、上报端点（内网自建网关域名占位如 `otlp.tageneval.internal`）；应用列表加 `接入通道` 列，取值限四通道
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 把某个面板的端点改成 `xxx.aliyuncs.com`，确认 Task 1 的禁用词断言转红；还原

**验收：** 本段 **0 FAIL**，累计 PASS ≥ 45

---

## Task 4: 链路观测与链路详情下钻

**Files:** Modify: `docs/prototype.html`、`docs/prototype.smoke.js`
**Depends on:** Task 3
**Interfaces:** `[data-drill^="trace:"]`、`[data-back]`、`[data-screen="trace"]`

- [x] Step 1: 写会失败的测试

```js
console.log("\n【10】链路观测与下钻");
// 挡的真实故障：行能点但跳过去是空壳，或详情页回不去列表
click($('.nav-item[data-go="traces"]'));
const trHeads = $$('[data-screen="traces"] table thead th').map((th) => th.textContent.trim());
["Trace ID","耗时","Total tokens","会话 ID"].forEach((h) =>
  ok(trHeads.some((x) => x.includes(h)), `Trace 列表含「${h}」列`));
const drill = $$('[data-screen="traces"] [data-drill^="trace:"]')[0];
ok(!!drill, "存在可下钻的 Trace 行");
const tid = drill.getAttribute("data-drill").split(":")[1];
click(drill);
ok(shown().length === 1 && shown()[0].getAttribute("data-screen") === "trace", "下钻到链路详情屏");
ok(txt('[data-screen="trace"]').includes(tid), `详情标题带被点行的 Trace ID（${tid}）`);
ok($$('[data-screen="trace"] [data-span]').length >= 3, "详情页有 span 树（≥3 个节点）");
click($('[data-screen="trace"] [data-back]'));
ok(shown().length === 1 && shown()[0].getAttribute("data-screen") === "traces", "返回链路列表");
```

- [x] Step 2: 跑，确认红
- [x] Step 3: 实现要点：`traces` 屏三视角页签（Trace 列表 / 会话分析 / Token 与成本）；Trace 列表按 spec 给列；行 `data-drill="trace:<id>"`；`trace` 屏渲染 span 树（缩进 + 耗时条）与 `[data-back]`
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 让 `data-back` 跳到 `dashboard`，确认返回断言转红；还原

**验收：** 本段 **0 FAIL**，累计 PASS ≥ 53

---

## Task 5: 数据魔方三屏

**Files:** Modify: `docs/prototype.html`、`docs/prototype.smoke.js`
**Depends on:** Task 4

- [x] Step 1: 写会失败的测试

```js
console.log("\n【11】数据魔方");
// 挡的真实故障：改名只改了菜单，屏内文案还写着旧口径；或「发起评估」是死按钮
const cubeNavs = $$(".nav-item").filter((n) =>
  ["trajectory","datasets","pipeline"].includes(n.getAttribute("data-go")));
ok(cubeNavs.length === 3, `数据魔方三屏导航齐备（${cubeNavs.length}/3）`);
click($('.nav-item[data-go="trajectory"]'));
const trjTxt = txt('[data-screen="trajectory"]');
ok(/Trace/.test(trjTxt) && /eBPF/.test(trjTxt), "轨迹库标明 Trace 与 eBPF 双数据源");
const trjHeads = $$('[data-screen="trajectory"] table thead th').map((t) => t.textContent.trim());
["Steps","工具调用","Tokens","耗时"].forEach((h) =>
  ok(trjHeads.some((x) => x.includes(h)), `轨迹库含「${h}」列`));

click($('.nav-item[data-go="datasets"]'));
click($('[data-screen="datasets"] [data-dlg="dlg-newds"]'));
const dsSrc = $$("#dlg-newds [data-dssrc]");
ok(dsSrc.length === 4, `数据集创建来源 ${dsSrc.length} 种（期望 4）`);
click(dsSrc[2]);
ok(dsSrc[2].classList.contains("on"), "来源可点选并高亮");
esc();
const dsRow = $$('[data-screen="datasets"] [data-drill^="dsdetail:"]')[0];
ok(!!dsRow, "数据集行可下钻");
click(dsRow);
["id","input","output","expected_output","trajectory"].forEach((f) =>
  ok(txt("[data-dsdetail]").includes(f), `数据集详情含字段 ${f}`));
click($("[data-dsdetail] [data-goeval]"));
ok(shown()[0].getAttribute("data-screen") === "tasks" && !$("#dlg-newtask").hasAttribute("hidden"),
   "「发起评估」跳到评估任务并打开新建弹窗");
esc();

click($('.nav-item[data-go="pipeline"]'));
const plTxt = txt('[data-screen="pipeline"]');
ok(/输入/.test(plTxt) && /(算子|处理)/.test(plTxt) && /输出/.test(plTxt), "流水线三段结构可见");
click($('[data-screen="pipeline"] [data-dlg="dlg-newpl"]'));
ok(/单次执行/.test(txt("#dlg-newpl")) && /周期执行/.test(txt("#dlg-newpl")), "两种调度模式可选");
esc();
```

- [x] Step 2: 跑，确认红
- [x] Step 3: 实现要点：三屏 + 两个创建弹窗；数据集详情用 `[data-dsdetail]` 区块（可以是同屏展开而非独立屏）；「发起评估」按钮调 `go('tasks')` 后 `openDlg('dlg-newtask')`
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 把「发起评估」改成只 `go('tasks')` 不开弹窗，确认断言转红；还原

**验收：** 本段 **0 FAIL**，累计 PASS ≥ 68

---

## Task 6: 评估器（DeepEval 预置 + 自定义 + 配置表单）

**Files:** Modify: `docs/prototype.html`、`docs/prototype.smoke.js`
**Depends on:** Task 5

- [x] Step 1: 写会失败的测试

```js
console.log("\n【12】评估器（DeepEval）");
// 挡的真实故障：阈值沿用 DeepEval 默认 0.5，与平台 τ=0.75 口径不符，评出来的结论全错
click($('.nav-item[data-go="evaluators"]'));
const evTxt = txt('[data-screen="evaluators"]');
const DEEPEVAL = ["AnswerRelevancyMetric","FaithfulnessMetric","ContextualRelevancyMetric",
  "ContextualPrecisionMetric","ContextualRecallMetric","TaskCompletionMetric","ToolCorrectnessMetric",
  "ArgumentCorrectnessMetric","TurnRelevancyMetric","RoleAdherenceMetric","KnowledgeRetentionMetric",
  "ConversationCompletenessMetric","HallucinationMetric","BiasMetric","ToxicityMetric","SummarizationMetric"];
const missing = DEEPEVAL.filter((m) => !evTxt.includes(m));
ok(missing.length === 0, `16 个 DeepEval 评估器齐备（缺 ${missing.length}：${missing.slice(0,3).join(",")}）`);
ok($$('.nav-item[data-go="metrics"]').length === 0 &&
   !/指标字典|指标库/.test(html), "无「指标字典/指标库」残留");
const evGroups = $$('[data-tab="evgroup"]');
ok(evGroups.length >= 4, `评估器分组页签 ${evGroups.length} 个（期望 ≥4）`);
let grpOk = 0;
evGroups.forEach((g) => {
  click(g);
  const rows = $$('[data-screen="evaluators"] tbody tr:not([hidden])').length;
  if (g.classList.contains("on") && rows > 0) grpOk++;
});
ok(grpOk === evGroups.length, `分组切换后列表非空（${grpOk}/${evGroups.length}）`);
click($$('[data-tab="evgroup"]').find((g) => g.getAttribute("data-tv") === "custom") || evGroups[0]);
ok(/GEval/.test(evTxt) && /DAGMetric/.test(evTxt), "自定义支持 GEval 与 DAGMetric");

click($('[data-screen="evaluators"] [data-dlg="dlg-newev"]'));
const thr = $('#dlg-newev [name="threshold"]');
ok(!!thr && thr.value === "0.75", `阈值默认 ${thr && thr.value}（期望 0.75，非 DeepEval 默认 0.5）`);
["threshold","model","include_reason","strict_mode","async_mode","verbose_mode"].forEach((f) =>
  ok(!!$(`#dlg-newev [name="${f}"]`), `配置表单含字段 ${f}`));
ok(/0\.5/.test(txt("#dlg-newev")), "表单内说明了与 DeepEval 默认 0.5 的差异");
esc();

console.log("\n【13】打分公式与三分量映射");
// 挡的真实故障：把「三分量怎么由 DeepEval 算」当成已定口径写死，实际还没确认
ok(/s_safety/.test(html) && /s_completion/.test(html) && /s_robustness/.test(html), "三分量出现");
ok(/0\.8/.test(html) && /0\.2/.test(html) && /0\.75/.test(html), "α=0.8 / β=0.2 / τ=0.75 出现");
ok(/pass@k/.test(html) && /pass\^k/.test(html), "pass@k 与 pass^k 出现");
const mapEls = $$("[data-map-status]");
ok(mapEls.length >= 1 && mapEls.some((e) => e.textContent.includes("待确认")),
   "三分量映射标注「待确认」");
```

- [x] Step 2: 跑，确认红
- [x] Step 3: 实现要点：预置/自定义两页签；预置按 4 组渲染 16 条，每条显示中文名 + 官方类名 + 分组徽章；创建弹窗六字段，`threshold` 默认 `0.75` 并在旁写明「平台口径 τ=0.75，DeepEval 默认为 0.5」；公式与三分量映射用一张小卡片呈现，映射处挂 `data-map-status` 徽标
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 把 `threshold` 默认值改回 `0.5`，确认断言转红；还原

**验收：** 本段 **0 FAIL**，累计 PASS ≥ 85

---

## Task 7: 评估任务、分析洞察与 Bad Case

**Files:** Modify: `docs/prototype.html`、`docs/prototype.smoke.js`
**Depends on:** Task 6

- [x] Step 1: 写会失败的测试

```js
console.log("\n【14】评估任务分步表单");
// 挡的真实故障：分步表单只能前进不能后退，填错了得重开
click($('.nav-item[data-go="tasks"]'));
click($('[data-screen="tasks"] [data-dlg="dlg-newtask"]'));
const step = (n) => $(`#dlg-newtask [data-step="${n}"]`);
ok(!step(1).hasAttribute("hidden") && step(2).hasAttribute("hidden"), "初始停在第 1 步");
["链路","Agent 轨迹","日志","数据集"].forEach((s) =>
  ok(txt("#dlg-newtask").includes(s), `数据来源含「${s}」`));
ok(/单轮对话/.test(txt("#dlg-newtask")) && /多轮对话/.test(txt("#dlg-newtask")), "评估粒度两选项");
ok(/基于新数据持续评估/.test(txt("#dlg-newtask")) && /基于历史数据评估/.test(txt("#dlg-newtask")),
   "两种运行策略");
const kIn = $('#dlg-newtask [name="k"]');
ok(!!kIn && kIn.value === "3", `试次 k 默认 ${kIn && kIn.value}（期望 3）`);
click($('#dlg-newtask [data-stepgo="2"]'));
ok(step(1).hasAttribute("hidden") && !step(2).hasAttribute("hidden"), "「下一步」切到第 2 步");
click($('#dlg-newtask [data-stepgo="1"]'));
ok(!step(1).hasAttribute("hidden") && step(2).hasAttribute("hidden"), "「上一步」切回第 1 步");
esc();

console.log("\n【15】分析洞察三口径");
// 挡的真实故障：只报 Average，掩盖了 pass^k 的稳定性问题
click($('.nav-item[data-go="insight"]'));
const insTxt = txt('[data-screen="insight"]');
["Average","pass@k","pass^k"].forEach((m) => ok(insTxt.includes(m), `分析洞察报「${m}」口径`));
const insHeads = $$('[data-screen="insight"] table thead th').map((t) => t.textContent.trim());
["原始分数","分数范围","归一化分数"].forEach((h) =>
  ok(insHeads.some((x) => x.includes(h)), `明细表含「${h}」列`));
const lowRow = $$('[data-screen="insight"] [data-drill^="trace:"]')[0];
ok(!!lowRow, "低分样本行可下钻");
click(lowRow);
ok(shown()[0].getAttribute("data-screen") === "trace", "低分样本下钻到链路详情");

console.log("\n【16】Bad Case 库");
click($('.nav-item[data-go="badcases"]'));
const bcHeads = $$('[data-screen="badcases"] table thead th').map((t) => t.textContent.trim());
["触发评估器","Root Cause"].forEach((h) =>
  ok(bcHeads.some((x) => x.includes(h)), `Bad Case 含「${h}」列`));
```

- [x] Step 2: 跑，确认红
- [x] Step 3: 实现要点：新建任务弹窗两步（数据配置 / 选择评估器），`[data-step]` + `[data-stepgo]`；分析洞察含三口径卡片 + 评分分布图 + 明细表；Bad Case 列表按 spec 给列，行可下钻
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 删掉「上一步」按钮，确认后退断言转红；还原

**验收：** 本段 **0 FAIL**，累计 PASS ≥ 103

---

## Task 8: 实验与回归（bullet 图）+ 持续优化两屏

**Files:** Modify: `docs/prototype.html`、`docs/prototype.smoke.js`
**Depends on:** Task 7

- [x] Step 1: 写会失败的测试

```js
console.log("\n【17】实验与回归门禁");
// 挡的真实故障：门禁结论没写清判定线，看不出为什么是「阻断」
click($('.nav-item[data-go="regression"]'));
const regTxt = txt('[data-screen="regression"]');
ok(/0\.75/.test(regTxt), "门禁展示判定线 τ=0.75");
ok(/(通过|阻断)/.test(regTxt), "展示门禁结论");
ok($$('[data-screen="regression"] [data-chart="bullet"]').length >= 1, "存在 bullet 形式的阈值对比图");

console.log("\n【18】图表可访问性");
// 挡的真实故障：多系列只靠颜色区分，色觉障碍或黑白打印时读不出来
const charts = $$("[data-chart]");
ok(charts.length >= 3, `图表 ${charts.length} 个（期望 ≥3）`);
const noTable = charts.filter((c) => {
  const box = c.closest("[data-chart-box]") || c.parentElement;
  return !box || !box.querySelector("[data-chart-table]");
});
ok(noTable.length === 0, `缺数据表 fallback 的图表 ${noTable.length} 个（期望 0）`);
const multi = $$('[data-chart="line-multi"]');
ok(multi.length >= 1 && multi.every((m) => m.querySelector("path[stroke-dasharray]")),
   "多系列折线用线型区分而非只靠颜色");

console.log("\n【19】持续优化两屏");
click($('.nav-item[data-go="assets"]'));
const asTxt = txt('[data-screen="assets"]');
ok(/Prompt/.test(asTxt) && /Skill/.test(asTxt), "Agent 资产含 Prompt 与 Skill");
ok(/(Latest|Production|版本)/.test(asTxt), "资产有版本概念");
click($('.nav-item[data-go="memory"]'));
const memTxt = txt('[data-screen="memory"]');
ok(/经验/.test(memTxt) && /记忆/.test(memTxt), "经验与记忆两类均呈现");
```

- [x] Step 2: 跑，确认红
- [x] Step 3: 实现要点：回归屏基线 vs 候选对比表 + bullet 图（横条 + 阈值刻度线）；每个图表包在 `[data-chart-box]` 内，内含 `[data-chart-table]` 可展开数据表；多系列折线用 `stroke-dasharray` 区分；资产屏两页签（Prompts / Skills）带版本列；记忆屏经验库 + 记忆库两页签
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 去掉某张图的 `[data-chart-table]`，确认 fallback 断言转红；还原

**验收：** 本段 **0 FAIL**，累计 PASS ≥ 115

---

## Task 9: 治理与系统五屏 + 总览与快速启动

**Files:** Modify: `docs/prototype.html`、`docs/prototype.smoke.js`
**Depends on:** Task 8

- [x] Step 1: 写会失败的测试

```js
console.log("\n【20】治理与系统");
// 挡的真实故障：风险审计与操作审计混成一屏，安全事件和人为操作分不开
ok($$('.nav-item[data-go="risk"]').length === 1 && $$('.nav-item[data-go="audit"]').length === 1,
   "风险审计与操作审计是两个独立屏");
click($('.nav-item[data-go="risk"]'));
const riskHeads = $$('[data-screen="risk"] table thead th').map((t) => t.textContent.trim());
["风险类型","等级"].forEach((h) => ok(riskHeads.some((x) => x.includes(h)), `风险审计含「${h}」列`));

click($('.nav-item[data-go="audit"]'));
const audHeads = $$('[data-screen="audit"] table thead th').map((t) => t.textContent.trim());
["操作人","操作","对象","结果","时间"].forEach((h) =>
  ok(audHeads.some((x) => x.includes(h)), `操作审计含「${h}」列`));
const visRows = () => $$('[data-screen="audit"] tbody tr').filter((r) => !r.hasAttribute("hidden")).length;
const beforeN = visRows();
click($('[data-screen="audit"] [data-hionly]'));
const afterN = visRows();
ok(afterN < beforeN && afterN > 0, `「仅看高风险」生效：${beforeN} → ${afterN} 行`);

click($('.nav-item[data-go="budget"]'));
const budTxt = txt('[data-screen="budget"]');
ok(/评测次数/.test(budTxt) && /Token/.test(budTxt), "两类配额齐备");
ok(/%/.test(budTxt), "显示用量占比");
ok($$("[data-quota-over]").length >= 1, "存在被标记的超额项");

click($('.nav-item[data-go="space"]'));
const roleVals = [...new Set($$('[data-screen="space"] [data-col="role"]').map((e) => e.textContent.trim()))];
ok(roleVals.length > 0 && roleVals.every((v) => ["管理员","测试开发","测试工程师","只读"].includes(v)),
   `成员角色取值合法：${roleVals.join("/")}`);

click($('.nav-item[data-go="notify"]'));
click($('[data-screen="notify"] [data-readall]'));
const badge = $("[data-unread]");
ok(!badge || badge.hasAttribute("hidden") || badge.textContent.trim() === "0", "全部已读后未读徽标归零");

console.log("\n【21】总览与快速启动");
click($('.nav-item[data-go="dashboard"]'));
ok($$('[data-screen="dashboard"] [data-kpi]').length >= 4,
   `总览指标卡 ${$$('[data-screen="dashboard"] [data-kpi]').length} 个（期望 ≥4）`);
click($('.nav-item[data-go="quickstart"]'));
const qsBtn = $$('[data-screen="quickstart"] [data-go]')[0];
ok(!!qsBtn, "快速启动有跳转按钮");
const qsTarget = qsBtn.getAttribute("data-go");
click(qsBtn);
ok(shown()[0].getAttribute("data-screen") === qsTarget &&
   $(`.nav-item[data-go="${qsTarget}"]`).classList.contains("on"),
   `快速启动跳转到 ${qsTarget} 且导航同步高亮`);
```

- [x] Step 2: 跑，确认红
- [x] Step 3: 实现要点：五屏按 spec 给列与控件；`[data-hionly]` 为 checkbox/开关，切换时对非高风险行增删 `hidden`；配额条超阈项挂 `data-quota-over` 并用 destructive 色；快速启动的引导按钮复用 `go()`
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 让「仅看高风险」不过滤，确认行数断言转红；还原

**验收：** 本段 **0 FAIL**，累计 PASS ≥ 135

---

## Task 10: 通用表格交互、静态校验与收口

**Files:** Modify: `docs/prototype.html`、`docs/prototype.smoke.js`；Modify: `agent-eval-platform/CLAUDE.md`（更新原型屏数与 smoke 基线数字）
**Depends on:** Task 9

- [x] Step 1: 写会失败的测试

```js
console.log("\n【22】通用表格交互");
// 挡的真实故障：排序/筛选/分页是静态装饰，点了数字不变，演示时被当场戳穿
click($('.nav-item[data-go="tasks"]'));
const sortTh = $$('[data-screen="tasks"] [data-sort]')[0];
ok(!!sortTh, "评估任务表有可排序列");
const firstCell = () => ($('[data-screen="tasks"] tbody tr td') || {}).textContent;
const v0 = firstCell();
click(sortTh);
const dir1 = sortTh.getAttribute("data-dir");
const v1 = firstCell();
click(sortTh);
const dir2 = sortTh.getAttribute("data-dir");
ok(dir1 && dir2 && dir1 !== dir2, `排序方向可翻转（${dir1} → ${dir2}）`);
ok(v1 !== v0 || firstCell() !== v1, "排序真实改变了行顺序");

const filt = $$('[data-screen="tasks"] [data-filter]')[0];
if (filt) {
  const n0 = $$('[data-screen="tasks"] tbody tr').filter((r) => !r.hasAttribute("hidden")).length;
  click(filt);
  const n1 = $$('[data-screen="tasks"] tbody tr').filter((r) => !r.hasAttribute("hidden")).length;
  ok(n1 !== n0, `筛选改变可见行数（${n0} → ${n1}）`);
} else ok(false, "评估任务表有筛选控件");

const pager = $('[data-screen="tasks"] [data-page="next"]');
if (pager) {
  const p0 = txt('[data-screen="tasks"] [data-pagenow]');
  click(pager);
  ok(txt('[data-screen="tasks"] [data-pagenow]') !== p0, `分页切换改变当前页（${p0} → ${txt('[data-screen="tasks"] [data-pagenow]')}）`);
} else ok(false, "评估任务表有分页控件");

console.log("\n【23】可访问性与响应式静态校验");
// 挡的真实故障：焦点环被抹掉、图标按钮没名字、表格撑破页面
const styleAll = $$("style").map((s) => s.textContent).join("\n");
const outlineNone = (styleAll.match(/[^}]*outline\s*:\s*none[^}]*}/g) || []);
const badOutline = outlineNone.filter((b) => !/(box-shadow|outline-offset|border-color)/.test(b));
ok(badOutline.length === 0, `无替代样式的 outline:none ${badOutline.length} 处（期望 0）`);
const iconBtns = $$("button").filter((b) => b.querySelector("svg") && !b.textContent.trim());
const noLabel = iconBtns.filter((b) => !(b.getAttribute("aria-label") || "").trim());
ok(noLabel.length === 0, `图标按钮缺 aria-label ${noLabel.length} 个（期望 0，共 ${iconBtns.length} 个）`);
ok(/prefers-reduced-motion/.test(styleAll), "存在 prefers-reduced-motion 兜底");
const tables = $$("table");
const unwrapped = tables.filter((t) => !t.closest(".table-wrap"));
ok(unwrapped.length === 0, `未包滚动容器的表格 ${unwrapped.length} 个（期望 0，共 ${tables.length} 个）`);
const EMOJI = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
ok(!EMOJI.test(doc.body.textContent), "正文无 emoji 当图标");
ok($$(".nav-item").every((n) => n.querySelector("svg")), "每个导航项都有 SVG 图标");

console.log("\n【24】运行时无错误");
ok(errs.length === 0, `无运行时错误（${errs.length}）${errs.slice(0,2).join(" | ")}`);

console.log(`\n${fail === 0 ? "✅" : "❌"} 通过 ${pass} / ${pass + fail}`);
process.exit(fail ? 1 : 0);
```

- [x] Step 2: 跑，确认红
- [x] Step 3: 实现要点
  - 通用 `sortTable/filterTable/pageTable` 三个函数，靠 `data-sort`/`data-filter`/`data-page` 委托绑定，各表复用
  - 补齐所有图标按钮的 `aria-label`、所有 `<table>` 的 `.table-wrap` 包裹、`prefers-reduced-motion` 块
  - **同步 `agent-eval-platform/CLAUDE.md`**：原型屏数 14 → 19、smoke 断言基线 28 → 本次实测值、「指标字典是单向同步的只读实体」一条改写为 DeepEval 口径
- [x] Step 4: 跑绿
- [x] Step 5: 反向验证 —— 移除某个图标按钮的 `aria-label`，确认断言转红；还原

**验收：**
- `cd agent-eval-platform/docs && node prototype.smoke.js` → **0 FAIL**，累计 PASS ≥ 150，退出码 0
- `grep -icE "agentloop|数据中心|aliyuncs|AI 积分" docs/prototype.html` → **0**
- 后端回归不受影响：`cd backend && DATABASE_URL="sqlite:///:memory:" .venv/Scripts/python.exe -m pytest tests/ -q` → **42 项通过**（基线，本次未动后端，若有失败即为「判不了」而非本次引入）

---

## 核心功能 E2E 覆盖

本次改动的核心功能是**原型本身**（它是界面的事实来源）。Task 1-10 的 smoke 断言即为其 E2E：覆盖 20 屏导航、三切换器、四通道、下钻返回、分步表单、三口径、门禁判定、表格交互、可访问性。**无遗漏项**；`docs/compare-with-prototype.js`（原型与实现比对脚本）在 Task 10 一并检查，若因结构变更失效则在交付报告中列出，不在本次修复。
