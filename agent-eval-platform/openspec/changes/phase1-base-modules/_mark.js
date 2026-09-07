/* 标记任务完成：node _mark.js 1.1 1.2 ...
 * 逐行字符串匹配，不用动态正则——拼正则在 shell 传参里容易丢转义。 */
const fs = require("fs");
const path = require("path");
const F = path.join(__dirname, "tasks.md");
const nums = process.argv.slice(2);
if (!nums.length) { console.error("用法: node _mark.js 1.1 1.2"); process.exit(2); }

const lines = fs.readFileSync(F, "utf8").split("\n");
const done = [];
nums.forEach((n) => {
  const i = lines.findIndex((l) => l.startsWith(`- [ ] ${n} `));
  if (i < 0) {
    const already = lines.some((l) => l.startsWith(`- [x] ${n} `));
    console.error(already ? `  已是完成态: ${n}` : `  ✗ 找不到待办任务: ${n}`);
    if (!already) process.exitCode = 1;
    return;
  }
  lines[i] = lines[i].replace("- [ ] ", "- [x] ");
  done.push(n);
});
fs.writeFileSync(F, lines.join("\n"));
const total = lines.filter((l) => /^- \[[ x]\] /.test(l)).length;
const complete = lines.filter((l) => l.startsWith("- [x] ")).length;
console.log(`已标记: ${done.join(", ") || "无"}  →  ${complete}/${total}`);
