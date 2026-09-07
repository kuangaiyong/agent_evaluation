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
/* 只取大括号内的声明再判断，否则选择器本身会被当成一条声明，断言永远为假 */
const darkDecls = darkBlocks
  .map((b) => b.slice(b.indexOf("{") + 1, b.lastIndexOf("}")))
  .join(";").split(";").map((s) => s.trim()).filter(Boolean);
const darkBad = darkDecls.filter((d) => !d.startsWith("--"));
ok(darkBlocks.length >= 1 && darkBad.length === 0,
   `暗色块内只覆写 token（越界声明 ${darkBad.length} 条）${darkBad.slice(0, 2).join(",")}`);

console.log("\n【4】字体与外链");
ok($$('script[src]').length === 0, "无外链脚本");
const fontLinks = $$('link[href*="fonts.googleapis.com"]');
ok(fontLinks.length === 1, `Google Fonts link ${fontLinks.length} 条（期望 1）`);
ok(fontLinks.length === 1 && /DM\+Sans/.test(fontLinks[0].href) &&
   /Space\+Grotesk/.test(fontLinks[0].href), "字体为 DM Sans + Space Grotesk");

console.log("\n【5】工作空间切换");
// 挡的真实故障：切了空间但页面上的当前空间名没跟着变，用户以为没切成功
const spaces = $$("[data-space]");
ok(spaces.length >= 3, `演示空间 ${spaces.length} 个（期望 ≥3）`);
/* 功能缺失时这些取值会是 undefined。不做保护的话脚本会崩在这里，
   崩溃点之后的断言一条都跑不到 —— 那是「判不了」，会被误读成「没问题」。 */
const target = spaces[1];
click(target);
ok(!!target && txt("[data-space-current]").includes(target.getAttribute("data-space")),
   `切换后当前空间名为 ${target ? target.getAttribute("data-space") : "(无空间切换器)"}`);
ok(!!target && target.classList.contains("on"), "被选空间带 .on");

console.log("\n【6】角色权限可见性");
// 挡的真实故障：切成只读角色后写操作按钮还在，点了才发现没权限
const roleBtn = (r) => $$("[data-role]").find((b) => b.getAttribute("data-role") === r);
const guarded = $$("[data-role-only]");
ok(guarded.length >= 8, `受角色管控的元素 ${guarded.length} 个（期望 ≥8）`);
click(roleBtn("viewer"));
const leak = guarded.filter((el) => !el.getAttribute("data-role-only").split(",").map((s) => s.trim()).includes("viewer")
                                 && !el.hasAttribute("hidden"));
ok(leak.length === 0, `只读角色下泄漏的写操作入口 ${leak.length} 个（期望 0）`);
click(roleBtn("admin"));
const adminOnly = guarded.filter((el) => el.getAttribute("data-role-only").split(",").map((s) => s.trim()).includes("admin"));
ok(adminOnly.every((el) => !el.hasAttribute("hidden")), "管理员下 admin 专属入口全部可见（角色切换可逆）");

console.log("\n【7】主题切换");
// 挡的真实故障：主题靠逐元素改内联样式，切一次漏一片
const rootEl = doc.documentElement;
const before = rootEl.getAttribute("data-theme") || "light";
click($("[data-theme-toggle]"));
const after = rootEl.getAttribute("data-theme");
ok(after !== before && ["light", "dark"].includes(after), `主题 ${before} → ${after}`);
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

console.log("\n【9】接入中心四通道");
// 挡的真实故障：接入指引写着云厂商端点或 LicenseKey，照着做接不通我们自建的网关
click($('.nav-item[data-go="access"]'));
const chTabs = $$('[data-tab="channel"]');
ok(chTabs.length === 4, `接入通道页签 ${chTabs.length} 个（期望 4）`);
ok(JSON.stringify(chTabs.map((t) => t.getAttribute("data-tv")).sort()) ===
   JSON.stringify(["ebpf", "otlp", "pilot", "py"]), "四通道标识齐备");
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
const chVals = [...new Set($$("#acTable tbody tr").map((tr) => {
  const c = tr.querySelector("[data-col='channel']");
  return c ? c.textContent.trim() : "";
}).filter(Boolean))];
ok(chVals.length > 0 && chVals.every((v) => ["Python Agent", "Pilot", "OTLP 直推", "eBPF"].includes(v)),
   `接入通道取值合法：${chVals.join("/")}`);

console.log("\n【10】链路观测与下钻");
// 挡的真实故障：行能点但跳过去是空壳，或详情页回不去列表
click($('.nav-item[data-go="traces"]'));
const trHeads = $$('[data-screen="traces"] table thead th').map((th) => th.textContent.trim());
["Trace ID", "耗时", "Total tokens", "会话 ID"].forEach((h) =>
  ok(trHeads.some((x) => x.includes(h)), `Trace 列表含「${h}」列`));
/* 必须点非首行：详情页的静态默认值就是首行的 ID，点首行时「不回填」也会假通过 */
const drillRows = $$('[data-screen="traces"] [data-drill^="trace:"]');
const drill = drillRows[1];
ok(drillRows.length >= 2 && !!drill, `可下钻的 Trace 行 ${drillRows.length} 条（取第 2 条以避开默认值巧合）`);
const tid = drill ? drill.getAttribute("data-drill").split(":")[1] : "";
click(drill);
ok(shown().length === 1 && shown()[0].getAttribute("data-screen") === "trace", "下钻到链路详情屏");
ok(txt('[data-screen="trace"]').includes(tid), `详情标题带被点行的 Trace ID（${tid}）`);
ok($$('[data-screen="trace"] [data-span]').length >= 3,
   `详情页有 span 树（${$$('[data-screen="trace"] [data-span]').length} 个节点，期望 ≥3）`);
click($('[data-screen="trace"] [data-back]'));
ok(shown().length === 1 && shown()[0].getAttribute("data-screen") === "traces", "返回链路列表");

console.log("\n【11】数据魔方");
// 挡的真实故障：改名只改了菜单，屏内文案还写着旧口径；或「发起评估」是死按钮
const cubeNavs = $$(".nav-item").filter((n) =>
  ["trajectory", "datasets", "pipeline"].includes(n.getAttribute("data-go")));
ok(cubeNavs.length === 3, `数据魔方三屏导航齐备（${cubeNavs.length}/3）`);
click($('.nav-item[data-go="trajectory"]'));
const trjTxt = txt('[data-screen="trajectory"]');
ok(/Trace/.test(trjTxt) && /eBPF/.test(trjTxt), "轨迹库标明 Trace 与 eBPF 双数据源");
const trjHeads = $$('[data-screen="trajectory"] table thead th').map((t) => t.textContent.trim());
["Steps", "工具调用", "Tokens", "耗时"].forEach((h) =>
  ok(trjHeads.some((x) => x.includes(h)), `轨迹库含「${h}」列`));

click($('.nav-item[data-go="datasets"]'));
click($('[data-screen="datasets"] [data-dlg="dlg-newds"]'));
const dsSrc = $$("#dlg-newds [data-dssrc]");
ok(dsSrc.length === 4, `数据集创建来源 ${dsSrc.length} 种（期望 4）`);
click(dsSrc[2]);
ok(dsSrc.length === 4 && dsSrc[2].classList.contains("on"), "来源可点选并高亮");
esc();
const dsRow = $$('[data-screen="datasets"] [data-drill^="dsdetail:"]')[0];
ok(!!dsRow, "数据集行可下钻");
click(dsRow);
["id", "input", "output", "expected_output", "trajectory"].forEach((f) =>
  ok(txt("[data-dsdetail]").includes(f), `数据集详情含字段 ${f}`));
click($("[data-dsdetail] [data-goeval]"));
ok(shown().length === 1 && shown()[0].getAttribute("data-screen") === "tasks" &&
   !$("#dlg-newtask").hasAttribute("hidden"),
   "「发起评估」跳到评估任务并打开新建弹窗");
esc();

click($('.nav-item[data-go="pipeline"]'));
const plTxt = txt('[data-screen="pipeline"]');
ok(/输入/.test(plTxt) && /(算子|处理)/.test(plTxt) && /输出/.test(plTxt), "流水线三段结构可见");
click($('[data-screen="pipeline"] [data-dlg="dlg-newpl"]'));
ok(/单次执行/.test(txt("#dlg-newpl")) && /周期执行/.test(txt("#dlg-newpl")), "两种调度模式可选");
esc();

console.log("\n【12】评估器（DeepEval）");
// 挡的真实故障：阈值沿用 DeepEval 默认 0.5，与平台 τ=0.75 口径不符，评出来的结论全错
click($('.nav-item[data-go="evaluators"]'));
const evTxt = txt('[data-screen="evaluators"]');
const DEEPEVAL = ["AnswerRelevancyMetric", "FaithfulnessMetric", "ContextualRelevancyMetric",
  "ContextualPrecisionMetric", "ContextualRecallMetric", "TaskCompletionMetric", "ToolCorrectnessMetric",
  "ArgumentCorrectnessMetric", "TurnRelevancyMetric", "RoleAdherenceMetric", "KnowledgeRetentionMetric",
  "ConversationCompletenessMetric", "HallucinationMetric", "BiasMetric", "ToxicityMetric", "SummarizationMetric"];
const missing = DEEPEVAL.filter((m) => !evTxt.includes(m));
ok(missing.length === 0, `16 个 DeepEval 评估器齐备（缺 ${missing.length}：${missing.slice(0, 3).join(",")}）`);
ok($$('.nav-item[data-go="metrics"]').length === 0 && !/指标字典|指标库/.test(html),
   "无「指标字典/指标库」残留");
const evGroups = $$('[data-tab="evgroup"]');
ok(evGroups.length >= 4, `评估器分组页签 ${evGroups.length} 个（期望 ≥4）`);
let grpOk = 0;
evGroups.forEach((g) => {
  click(g);
  const rows = $$('[data-screen="evaluators"] tbody tr').filter((r) => !r.hasAttribute("hidden")).length;
  if (g.classList.contains("on") && rows > 0) grpOk++;
});
ok(grpOk === evGroups.length, `分组切换后列表非空（${grpOk}/${evGroups.length}）`);
const customTab = evGroups.find((g) => g.getAttribute("data-tv") === "custom");
click(customTab);
ok(/GEval/.test(evTxt) && /DAGMetric/.test(evTxt), "自定义支持 GEval 与 DAGMetric");

click($('[data-screen="evaluators"] [data-dlg="dlg-newev"]'));
const thr = $('#dlg-newev [name="threshold"]');
ok(!!thr && thr.value === "0.75", `阈值默认 ${thr ? thr.value : "(无字段)"}（期望 0.75，非 DeepEval 默认 0.5）`);
["threshold", "model", "include_reason", "strict_mode", "async_mode", "verbose_mode"].forEach((f) =>
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

console.log("\n【14】评估任务分步表单");
// 挡的真实故障：分步表单只能前进不能后退，填错了得重开
click($('.nav-item[data-go="tasks"]'));
click($('[data-screen="tasks"] [data-dlg="dlg-newtask"]'));
const step = (n) => $(`#dlg-newtask [data-step="${n}"]`);
ok(!!step(1) && !!step(2) && !step(1).hasAttribute("hidden") && step(2).hasAttribute("hidden"),
   "初始停在第 1 步");
["链路", "Agent 轨迹", "日志", "数据集"].forEach((src) =>
  ok(txt("#dlg-newtask").includes(src), `数据来源含「${src}」`));
ok(/单轮对话/.test(txt("#dlg-newtask")) && /多轮对话/.test(txt("#dlg-newtask")), "评估粒度两选项");
ok(/基于新数据持续评估/.test(txt("#dlg-newtask")) && /基于历史数据评估/.test(txt("#dlg-newtask")),
   "两种运行策略");
const kIn = $('#dlg-newtask [name="k"]');
ok(!!kIn && kIn.value === "3", `试次 k 默认 ${kIn ? kIn.value : "(无字段)"}（期望 3）`);
click($('#dlg-newtask [data-stepgo="2"]'));
ok(!!step(1) && step(1).hasAttribute("hidden") && !step(2).hasAttribute("hidden"), "「下一步」切到第 2 步");
click($('#dlg-newtask [data-stepgo="1"]'));
ok(!!step(1) && !step(1).hasAttribute("hidden") && step(2).hasAttribute("hidden"), "「上一步」切回第 1 步");
esc();

console.log("\n【15】分析洞察三口径");
// 挡的真实故障：只报 Average，掩盖了 pass^k 的稳定性问题
click($('.nav-item[data-go="insight"]'));
const insTxt = txt('[data-screen="insight"]');
["Average", "pass@k", "pass^k"].forEach((m) => ok(insTxt.includes(m), `分析洞察报「${m}」口径`));
const insHeads = $$('[data-screen="insight"] table thead th').map((t) => t.textContent.trim());
["原始分数", "分数范围", "归一化分数"].forEach((h) =>
  ok(insHeads.some((x) => x.includes(h)), `明细表含「${h}」列`));
const lowRows = $$('[data-screen="insight"] [data-drill^="trace:"]');
ok(lowRows.length >= 2, `低分样本可下钻（${lowRows.length} 行）`);
click(lowRows[1]);
ok(shown().length === 1 && shown()[0].getAttribute("data-screen") === "trace", "低分样本下钻到链路详情");

console.log("\n【16】Bad Case 库");
click($('.nav-item[data-go="badcases"]'));
const bcHeads = $$('[data-screen="badcases"] table thead th').map((t) => t.textContent.trim());
["触发评估器", "Root Cause"].forEach((h) =>
  ok(bcHeads.some((x) => x.includes(h)), `Bad Case 含「${h}」列`));

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
ok(multi.length >= 1 && multi.every((m) => m.querySelector("path[stroke-dasharray], polyline[stroke-dasharray]")),
   `多系列折线用线型区分而非只靠颜色（${multi.length} 张）`);

console.log("\n【19】持续优化两屏");
/* 只断言「屏内出现某个词」太弱：Task 2 加的操作栏与屏描述里本来就有这些词，
   两屏一行内容不写也能通过。改为断言页签可切换 + 表格有实际行。 */
click($('.nav-item[data-go="assets"]'));
const asTabs = $$('[data-tab="asset"]');
ok(asTabs.length === 2, `Agent 资产两个页签（${asTabs.length}/2）`);
let asOk = 0;
asTabs.forEach((t) => {
  click(t);
  const vis = $$("[data-aspane]").filter((x) => !x.hasAttribute("hidden"));
  if (vis.length === 1 && vis[0].getAttribute("data-aspane") === t.getAttribute("data-tv")) asOk++;
});
ok(asOk === 2, `资产页签切换生效（${asOk}/2）`);
const asHeads = $$('[data-screen="assets"] table thead th').map((t) => t.textContent.trim());
ok(asHeads.some((h) => h.includes("版本")), `资产表含「版本」列：${asHeads.join("/")}`);
ok(/Latest/.test(txt('[data-screen="assets"]')) && /Production/.test(txt('[data-screen="assets"]')),
   "资产区分 Latest 与 Production 双通道");
ok($$('[data-screen="assets"] tbody tr').length >= 3,
   `资产列表有实际数据（${$$('[data-screen="assets"] tbody tr').length} 行）`);

click($('.nav-item[data-go="memory"]'));
const memTabs = $$('[data-tab="mem"]');
ok(memTabs.length === 2, `经验与记忆两个页签（${memTabs.length}/2）`);
let memOk = 0;
memTabs.forEach((t) => {
  click(t);
  const vis = $$("[data-mempane]").filter((x) => !x.hasAttribute("hidden"));
  if (vis.length === 1 && vis[0].getAttribute("data-mempane") === t.getAttribute("data-tv")) memOk++;
});
ok(memOk === 2, `记忆页签切换生效（${memOk}/2）`);
ok($$('[data-screen="memory"] tbody tr').length >= 3,
   `经验/记忆有实际数据（${$$('[data-screen="memory"] tbody tr').length} 行）`);

console.log("\n【20】治理与系统");
// 挡的真实故障：风险审计与操作审计混成一屏，安全事件和人为操作分不开
ok($$('.nav-item[data-go="risk"]').length === 1 && $$('.nav-item[data-go="audit"]').length === 1,
   "风险审计与操作审计是两个独立屏");
click($('.nav-item[data-go="risk"]'));
const riskHeads = $$('[data-screen="risk"] table thead th').map((t) => t.textContent.trim());
["风险类型", "等级"].forEach((h) => ok(riskHeads.some((x) => x.includes(h)), `风险审计含「${h}」列`));

click($('.nav-item[data-go="audit"]'));
const audHeads = $$('[data-screen="audit"] table thead th').map((t) => t.textContent.trim());
["操作人", "操作", "对象", "结果", "时间"].forEach((h) =>
  ok(audHeads.some((x) => x.includes(h)), `操作审计含「${h}」列`));
const visRows = () => $$('[data-screen="audit"] tbody tr').filter((r) => !r.hasAttribute("hidden")).length;
const beforeN = visRows();
click($('[data-screen="audit"] [data-hionly]'));
const afterN = visRows();
ok(afterN < beforeN && afterN > 0, `「仅看高风险」生效：${beforeN} → ${afterN} 行`);
const leftHi = $$('[data-screen="audit"] tbody tr').filter((r) => !r.hasAttribute("hidden"));
ok(leftHi.every((r) => r.getAttribute("data-hi") === "1"), "剩余行均为高风险");

click($('.nav-item[data-go="budget"]'));
const budTxt = txt('[data-screen="budget"]');
ok(/评测次数/.test(budTxt) && /Token/.test(budTxt), "两类配额齐备");
ok(/%/.test(budTxt), "显示用量占比");
ok($$("[data-quota-over]").length >= 1, `存在被标记的超额项（${$$("[data-quota-over]").length} 个）`);

click($('.nav-item[data-go="space"]'));
const roleVals = [...new Set($$('[data-screen="space"] [data-col="role"]').map((e) => e.textContent.trim()))];
ok(roleVals.length > 0 && roleVals.every((v) => ["管理员", "测试开发", "测试工程师", "只读"].includes(v)),
   `成员角色取值合法：${roleVals.join("/")}`);

click($('.nav-item[data-go="notify"]'));
const badgeBefore = $("[data-unread]");
ok(!!badgeBefore && badgeBefore.textContent.trim() !== "0", `未读徽标初始有值（${badgeBefore ? badgeBefore.textContent.trim() : "无"}）`);
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
const qsTarget = qsBtn ? qsBtn.getAttribute("data-go") : "";
click(qsBtn);
ok(!!qsBtn && shown().length === 1 && shown()[0].getAttribute("data-screen") === qsTarget &&
   $(`.nav-item[data-go="${qsTarget}"]`).classList.contains("on"),
   `快速启动跳转到 ${qsTarget} 且导航同步高亮`);

console.log("\n【22】通用表格交互");
// 挡的真实故障：排序/筛选/分页是静态装饰，点了数字不变，演示时被当场戳穿
click($('.nav-item[data-go="tasks"]'));
const sortTh = $$('[data-screen="tasks"] [data-sort]')[0];
ok(!!sortTh, "评估任务表有可排序列");
const firstCell = () => {
  const c = $('[data-screen="tasks"] tbody tr td');
  return c ? c.textContent.trim() : "";
};
const v0 = firstCell();
click(sortTh);
const dir1 = sortTh ? sortTh.getAttribute("data-dir") : null;
const v1 = firstCell();
click(sortTh);
const dir2 = sortTh ? sortTh.getAttribute("data-dir") : null;
ok(!!dir1 && !!dir2 && dir1 !== dir2, `排序方向可翻转（${dir1} → ${dir2}）`);
ok(v1 !== v0 || firstCell() !== v1, `排序真实改变了行顺序（${v0} → ${v1} → ${firstCell()}）`);

const filt = $$('[data-screen="tasks"] [data-filter]')[1];
const visTaskRows = () => $$('[data-screen="tasks"] tbody tr').filter((r) => !r.hasAttribute("hidden")).length;
const n0 = visTaskRows();
click(filt);
const n1 = visTaskRows();
ok(!!filt && n1 !== n0 && n1 > 0, `筛选改变可见行数（${n0} → ${n1}）`);
const fv = filt ? filt.getAttribute("data-filter") : "";
ok($$('[data-screen="tasks"] tbody tr').filter((r) => !r.hasAttribute("hidden"))
    .every((r) => r.getAttribute("data-filter-status") === fv), "剩余行均匹配筛选条件");
click($$('[data-screen="tasks"] [data-filter]')[0]);

const pager = $('[data-screen="tasks"] [data-page="next"]');
const p0 = txt('[data-screen="tasks"] [data-pagenow]');
click(pager);
ok(!!pager && txt('[data-screen="tasks"] [data-pagenow]') !== p0,
   `分页切换改变当前页（${p0} → ${txt('[data-screen="tasks"] [data-pagenow]')}）`);

console.log("\n【23】可访问性与响应式静态校验");
// 挡的真实故障：焦点环被抹掉、图标按钮没名字、表格撑破页面
const styleAll = $$("style").map((s) => s.textContent).join("\n");
const outlineNone = styleAll.match(/[^{}]*\{[^}]*outline\s*:\s*none[^}]*\}/g) || [];
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
/* Task 1 自审发现 rgb() 字面量能绕过 #hex 检查，这里补上自动断言 */
const nonTokenCss = styleAll.replace(/:root\s*\{[^}]*\}/g, "").replace(/\[data-theme=["']?dark["']?\]\s*\{[^}]*\}/g, "");
const rawRgb = nonTokenCss.match(/rgba?\([^)]*\)/g) || [];
ok(rawRgb.length === 0, `组件规则内 rgb() 字面量 ${rawRgb.length} 处（期望 0）${rawRgb.slice(0, 2).join(",")}`);

console.log("\n【24】运行时无错误");
ok(errs.length === 0, `无运行时错误（${errs.length}）${errs.slice(0, 2).join(" | ")}`);

console.log(`\n${fail === 0 ? "✅" : "❌"} 通过 ${pass} / ${pass + fail}`);
process.exit(fail ? 1 : 0);
