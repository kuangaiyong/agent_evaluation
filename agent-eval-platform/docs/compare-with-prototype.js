/* 原型 ↔ 实现 结构对比
 *
 *   node docs/compare-with-prototype.js
 *   退出码 0 = 无差异，1 = 有差异（可当门禁用）
 *
 * 为什么要有它：docs/prototype.html 是界面的事实来源，但「页签顺序反了」「少两列」
 * 这类差异肉眼最容易放过，人工对截图也不可重复。这个脚本从两侧各自抽取三类结构
 * ——导航（一级分组 → 二级菜单 → 路由）、页签清单、表格列名——逐项比对。
 *
 * 已知抽取局限（差异清零不等于完全一致，7.4 的人工过屏是兜底）：
 *   1. 只识别静态声明的 <el-table-column label="..."> 与 <el-tab-pane label="...">。
 *      用 v-for 动态生成的列、或 label 绑定变量的（:label="x"）一律漏检。
 *   2. 原型侧的 <th> 会把覆盖度矩阵这类非数据表的表头也算进来，故按屏配置
 *      SKIP_TABLE 跳过。
 *   3. 只比结构，不比数据、状态与样式。
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const PROTO = path.join(ROOT, "docs", "prototype.html");
const SRC = path.join(ROOT, "frontend", "src");

/* 屏 id ↔ Vue 页面。null 表示该屏在实现侧应有独立页面但可能尚未建立 */
const SCREENS = {
  dashboard: "Dashboard",
  onboard: "Onboarding",
  access: "Access",
  traces: "Traces",
  trace: "TraceDetail",
  metrics: "Metrics",
  evaluators: "Evaluators",
  tasks: "Tasks",
  badcases: "BadCases",
  datacenter: "Datacenter",
  regression: "Regression",
  audit: "Audit",
  system: "System",
  notifications: "Notifications",
};

/* 不参与列比对的屏：其表格不是数据表，或本期不在范围内 */
const SKIP_TABLE = new Set([
  "metrics",      // 覆盖度矩阵的表头不是数据列
  "budget",       // 一期不在范围
  "notifications", // 一期不动
]);

/* 一期不比对的屏（范围外，见 proposal.md） */
const OUT_OF_SCOPE = new Set(["budget", "notifications"]);

const read = (p) => fs.readFileSync(p, "utf8").replace(/\r\n/g, "\n");
/* 原型里的 .mk 徽章（「新增」「建议下线」）是取舍标记，不是界面文案，抽取时先剥掉 */
const clean = (s) =>
  s.replace(/<span class="mk[^"]*">[\s\S]*?<\/span>/g, "")
    .replace(/<[^>]*>/g, "")
    .replace(/\s+/g, " ")
    .trim();

/* 一期与原型的刻意偏差（design.md D5）：
 * 原型把「操作审计」与「成本与配额」并列在「成本与治理」下，但成本与配额不在一期，
 * 一个只含审计的分组会让人误以为这里有成本功能。故一期把它挂在「系统管理」下。
 * 这里把目标结构编码进来，避免这处已决策的偏差被永久报成差异。 */
const NAV_OVERRIDE = { audit: "系统管理" };

/* 一期范围外的列：原型上有，但对应能力不在本期。
 * 「日额度」属于「成本与配额」模块（proposal 明确推后），specs/system-management
 * 也没有要求它。等成本与配额落地时把这条删掉，差异会自然重新出现。 */
const OUT_OF_SCOPE_COLS = { System: ["日额度"] };

// ───────────────────────── 原型侧 ─────────────────────────

const proto = read(PROTO);

function protoNav() {
  const nav = proto.match(/<nav id="nav">([\s\S]*?)<\/nav>/)[1];
  const groups = [];
  let cur = null;
  nav.split("\n").forEach((line) => {
    const g = line.match(/<div class="nav-label">([^<]+)</);
    if (g) { cur = { group: g[1].trim(), items: [] }; groups.push(cur); return; }
    const m = line.match(/data-go="([^"]+)"[\s\S]*?class="nm">([^<]+)</);
    if (m && cur) cur.items.push({ name: clean(m[2]), screen: m[1] });
  });
  return groups;
}

function protoScreen(id) {
  const marker = `data-screen="${id}"`;
  const i = proto.indexOf(marker);
  if (i < 0) return null;
  const start = proto.lastIndexOf("<section", i);
  const end = proto.indexOf("</section>", i);
  return proto.slice(start, end);
}

function protoTabs(id) {
  const s = protoScreen(id);
  if (!s) return [];
  return [...s.matchAll(/<button class="tab[^"]*"[^>]*data-t="[^"]+">([\s\S]*?)<\/button>/g)]
    .map((m) => clean(m[1]));
}

function protoCols(id) {
  const s = protoScreen(id);
  if (!s || SKIP_TABLE.has(id)) return [];
  return [...s.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)]
    .map((m) => clean(m[1]))
    .filter((x) => x && !/^[·\d\s]*$/.test(x));
}

// ───────────────────────── 实现侧 ─────────────────────────

function vueFile(name) {
  const p = path.join(SRC, "pages", `${name}.vue`);
  return fs.existsSync(p) ? read(p) : null;
}

function codeNav() {
  const layout = read(path.join(SRC, "layout", "MainLayout.vue"));
  const block = layout.match(/const navGroups\s*=\s*\[([\s\S]*?)\n\]/);
  if (!block) return [];
  const groups = [];
  let cur = null;
  block[1].split("\n").forEach((line) => {
    const g = line.match(/label:\s*'([^']+)'/);
    if (g) { cur = { group: g[1], items: [] }; groups.push(cur); return; }
    const m = line.match(/path:\s*'([^']+)'\s*,\s*name:\s*'([^']+)'/);
    if (m && cur) cur.items.push({ name: m[2], route: m[1] });
  });
  return groups;
}

const vueTabs = (html) => (html ? [...html.matchAll(/<el-tab-pane[^>]*\blabel="([^"]+)"/g)].map((m) => m[1]) : []);
const vueCols = (html) => (html ? [...html.matchAll(/<el-table-column[^>]*\blabel="([^"]+)"/g)].map((m) => m[1]) : []);

// ───────────────────────── 比对 ─────────────────────────

const diffs = [];
const add = (area, detail) => diffs.push({ area, detail });

/* 1. 导航：分组名、二级菜单名、菜单项数 */
function compareNav() {
  const p = protoNav().filter((g) => g.items.some((i) => !OUT_OF_SCOPE.has(i.screen)));
  const c = codeNav();

  // 原型侧剔除范围外的菜单项，再按 NAV_OVERRIDE 把已决策要挪窝的项移到目标分组，
  // 最后剔掉因此变空的分组
  const pTrim = p
    .map((g) => ({ group: g.group, items: g.items.filter((i) => !OUT_OF_SCOPE.has(i.screen)) }))
    .map((g) => ({ group: g.group, items: g.items.filter((i) => (NAV_OVERRIDE[i.screen] || g.group) === g.group) }));
  Object.entries(NAV_OVERRIDE).forEach(([screen, target]) => {
    const moved = p.flatMap((g) => g.items).find((i) => i.screen === screen);
    const dest = pTrim.find((g) => g.group === target);
    if (moved && dest && !dest.items.some((i) => i.screen === screen)) dest.items.push(moved);
  });
  const pKeep = pTrim.filter((g) => g.items.length);
  const cTrim = c
    .map((g) => ({ group: g.group, items: g.items.filter((i) => !/notifications/.test(i.route)) }))
    .filter((g) => g.items.length);

  const pNames = pKeep.map((g) => g.group);
  const cNames = cTrim.map((g) => g.group);
  if (pNames.join("|") !== cNames.join("|")) {
    add("导航分组", `原型 [${pNames.join(", ")}]  实现 [${cNames.join(", ")}]`);
  }

  pKeep.forEach((pg) => {
    const cg = cTrim.find((x) => x.group === pg.group);
    if (!cg) { add("导航分组", `实现缺少分组「${pg.group}」`); return; }
    const pi = pg.items.map((i) => i.name);
    const ci = cg.items.map((i) => i.name);
    if (pi.join("|") !== ci.join("|")) {
      add("二级菜单", `「${pg.group}」原型 [${pi.join(", ")}]（${pi.length} 项）  实现 [${ci.join(", ")}]（${ci.length} 项）`);
    }
  });
  cTrim.forEach((cg) => {
    if (!pKeep.find((x) => x.group === cg.group)) add("导航分组", `实现多出分组「${cg.group}」`);
  });
}

/* 2. 逐屏：页面存在性、页签、表格列 */
function compareScreens() {
  Object.entries(SCREENS).forEach(([id, vue]) => {
    if (OUT_OF_SCOPE.has(id)) return;
    const p = protoScreen(id);
    if (!p) return;
    const html = vueFile(vue);
    if (!html) { add("缺页面", `原型有 ${id} 屏，实现缺 pages/${vue}.vue`); return; }

    const pt = protoTabs(id), vt = vueTabs(html);
    if (pt.join("|") !== vt.join("|")) {
      // 页签文案两侧措辞可能不同，先比数量与顺序特征，再报全文
      add("页签", `${vue}: 原型 [${pt.join(", ")}]  实现 [${vt.join(", ")}]`);
    }

    const pc = protoCols(id), vc = vueCols(html);
    const skip = OUT_OF_SCOPE_COLS[vue] || [];
    const missing = pc.filter((c) => !vc.includes(c) && !skip.includes(c));
    if (missing.length) add("表格列", `${vue}: 实现缺 [${missing.join(", ")}]`);
  });
}

compareNav();
compareScreens();

// ───────────────────────── 输出 ─────────────────────────

if (!diffs.length) {
  console.log("✅ 原型与实现结构一致（导航 / 页签 / 表格列）");
  console.log("   注意：脚本不校验动态生成的列、数据与样式，人工过屏仍是兜底。");
  process.exit(0);
}

const byArea = {};
diffs.forEach((d) => (byArea[d.area] = byArea[d.area] || []).push(d.detail));
console.log(`❌ 发现 ${diffs.length} 处差异\n`);
Object.entries(byArea).forEach(([area, items]) => {
  console.log(`【${area}】`);
  items.forEach((d) => console.log("  · " + d));
  console.log("");
});
process.exit(1);
