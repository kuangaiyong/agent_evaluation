/* 原型交互冒烟测试
 *
 *   cd agent-eval-platform/docs && npm i jsdom && node prototype.smoke.js
 *
 * 为什么要有它：静态 grep 只能证明 data-* 属性写对了，证明不了「点得动」。
 * 这个文件用 jsdom 真正执行页面脚本并模拟点击，覆盖导航切屏、弹窗开关、
 * 表格行下钻、筛选、排序、页签与 toast。改原型后必须跑通再提交。 */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync("prototype.html", "utf8");
const dom = new JSDOM(`<!doctype html><html><head></head><body>${html}</body></html>`, {
  runScripts: "dangerously", pretendToBeVisual: true,
});
const { window } = dom;
const doc = window.document;
const $ = (s) => doc.querySelector(s);
const $$ = (s) => [...doc.querySelectorAll(s)];
const click = (el) => el.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));

let pass = 0, fail = 0;
const ok = (cond, msg) => { cond ? (pass++, console.log("  ✓ " + msg)) : (fail++, console.log("  ✗ " + msg)); };
const esc = () => doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));

console.log("\n【1】导航：13 项逐个点，屏幕是否真的切换");
const navs = $$(".nav-item");
ok(navs.length === 13, `导航项 ${navs.length} 个`);
let navOk = 0;
navs.forEach((b) => {
  click(b);
  const target = b.getAttribute("data-go");
  const scr = doc.querySelector(`[data-screen="${target}"]`);
  const visible = $$("[data-screen]").filter((x) => !x.hasAttribute("hidden"));
  if (scr && !scr.hasAttribute("hidden") && visible.length === 1 && b.classList.contains("on")) navOk++;
});
ok(navOk === 13, `13 个导航项全部切换成功（实到 ${navOk}）· 每次只有 1 屏可见 · 高亮跟随`);

console.log("\n【2】弹窗：每个 data-dlg 按钮都要真打开对应弹窗");
const dlgBtns = $$("[data-dlg]");
let dlgOk = 0;
dlgBtns.forEach((b) => {
  click(b);
  const box = doc.getElementById(b.getAttribute("data-dlg"));
  const on = box && box.classList.contains("on") && $("#ovl").classList.contains("on");
  esc();
  const closed = box && !box.classList.contains("on") && !$("#ovl").classList.contains("on");
  if (on && closed) dlgOk++;
});
ok(dlgOk === dlgBtns.length, `${dlgBtns.length} 个弹窗按钮全部可开可关（Esc 关闭，实到 ${dlgOk}）`);

console.log("\n【3】弹窗内的提交按钮：关闭弹窗并弹出 toast");
click($("[data-dlg='dlg-app']"));
const submit = $("#dlg-app [data-act]");
click(submit);
ok(!$("#dlg-app").classList.contains("on"), "提交后弹窗关闭");
ok($("#toast").classList.contains("on"), "提交后 toast 弹出");
ok($("#toast span").textContent.includes("API Key"), `toast 文案：「${$("#toast span").textContent}」`);

console.log("\n【4】表格行下钻：点行开抽屉，且内容由该行填充");
click($("[data-go='badcases']"));
const bcRow = $("#sc-bc tbody tr");
click(bcRow);
ok($("#drw-case").classList.contains("on"), "Bad Case 行 → 复核抽屉打开");
ok($("#drw-case [data-slot='title']").textContent.trim().startsWith("bc-"),
   `抽屉标题取自该行：「${$("#drw-case [data-slot='title']").textContent.trim()}」`);
esc();

click($("[data-go='metrics']"));
const mxRow = $("#sc-mx tbody tr");
click(mxRow);
const rows = $$("#drw-row [data-rows] .dsec").map((e) => e.textContent);
ok($("#drw-row").classList.contains("on"), "指标库行 → 通用详情抽屉打开");
ok(rows.length >= 4, `抽屉按表头生成 ${rows.length} 组字段：${rows.slice(0, 4).join(" / ")}`);
ok($("#drw-row [data-rowact]").getAttribute("data-act").includes("评估器"),
   `底部操作按钮随表切换：「${$("#drw-row [data-rowact]").textContent}」`);
esc();

console.log("\n【5】筛选：下拉与搜索真的过滤行");
click($("[data-go='traces']"));
const trRows = () => $$("#sc-tr tbody tr");
const shown = () => trRows().filter((r) => !r.classList.contains("hide")).length;
const total = trRows().length;
ok(shown() === total, `初始全部可见 ${total} 行`);

const appSel = $("select[data-filter='sc-tr'][data-col='2']");
appSel.value = "客服助手";
appSel.dispatchEvent(new window.Event("change", { bubbles: true }));
ok(shown() === 2 && shown() < total, `按应用筛选「客服助手」→ ${shown()} / ${total} 行`);
ok($(".cnt[data-cnt='sc-tr']").textContent.includes(`命中 ${shown()}`), `计数同步更新：「${$(".cnt[data-cnt='sc-tr']").textContent}」`);

const kw = $("input[data-filter='sc-tr']");
kw.value = "se-2c8590";
kw.dispatchEvent(new window.Event("input", { bubbles: true }));
ok(shown() === 1, `叠加关键词后取交集 → ${shown()} 行`);

kw.value = "不存在的ID";
kw.dispatchEvent(new window.Event("input", { bubbles: true }));
ok(shown() === 0 && !$(".empty[data-empty='sc-tr']").hidden, "无匹配时显示空态提示");

click($("[data-reset='sc-tr']"));
ok(shown() === total, `重置后恢复 ${shown()} 行`);

console.log("\n【6】仅高风险开关：只留打了 data-flag 的行");
click($("[data-go='audit']"));
const auRows = () => $$("#sc-au tbody tr");
const auShown = () => auRows().filter((r) => !r.classList.contains("hide")).length;
const auTotal = auRows().length;
const tg = $("button[data-filter='sc-au']");
click(tg);
ok(tg.classList.contains("on"), "开关进入选中态");
ok(auShown() === 3, `仅高风险 → ${auShown()} / ${auTotal} 行（应为 3 行）`);
click(tg);
ok(auShown() === auTotal, `再点取消 → 恢复 ${auShown()} 行`);

console.log("\n【7】排序：点表头真的重排");
click($("[data-go='traces']"));
const tokCol = $$("#sc-tr thead th").findIndex((t) => t.textContent.includes("Token"));
const tokens = () => $$("#sc-tr tbody tr").map((r) => parseFloat(r.cells[tokCol].innerHTML.replace(/[^\d.]/g, "")) || 0);
const before = tokens().join(",");
const th = $$("#sc-tr thead th")[tokCol];
click(th);
const desc = tokens();
ok(desc.join(",") !== before, "点击表头后行序发生变化");
ok(desc.every((v, i) => i === 0 || desc[i - 1] >= v), `降序正确：${desc.join(" ≥ ")}`);
click(th);
const asc = tokens();
ok(asc.every((v, i) => i === 0 || asc[i - 1] <= v), `再点转升序：${asc.join(" ≤ ")}`);

console.log("\n【8】页签与取舍标记开关");
click($("[data-go='tasks']"));
const tabs = $$("[data-tabs='tk'] .tab");
click(tabs[1]);
ok(tabs[1].classList.contains("on") && !doc.querySelector("[data-pane='tk-on']").hasAttribute("hidden"),
   "页签切换：面板跟随显示");
const tgl = $("#tglMarks");
click(tgl);
ok(doc.body.classList.contains("marks") && tgl.getAttribute("aria-pressed") === "true", "取舍标记开关生效");
click(tgl);
ok(!doc.body.classList.contains("marks"), "再点关闭");

console.log("\n【9】通知中心：全部已读");
click($("[data-go='notifications']"));
const unreadBefore = $$(".nf.un").length;
click($("[data-readall]"));
ok(unreadBefore > 0 && $$(".nf.un").length === 0, `${unreadBefore} 条未读 → 全部清除`);

console.log("\n【10】控制台是否有报错");
const errs = [];
window.addEventListener("error", (e) => errs.push(e.message));
ok(errs.length === 0, `无运行时错误（${errs.length}）`);

console.log(`\n${fail === 0 ? "✅" : "❌"} 通过 ${pass} / ${pass + fail}`);
process.exit(fail ? 1 : 0);
