---
name: ageval-doc-check
description: 智能体评测体系文档仓库的 5 项校验不变量（Mermaid 可渲染 / YAML 可解析 / rubric 自身 lint / 链接与锚点 / 图号与 SVG）与当前基线数字，以及写校验脚本时踩过的三个坑（CRLF、坏好并排的 yaml 块、grep 碰中文路径静默失败）。改完任何文档后跑校验时读这份。
---

## 校验（任何改动后必跑）

仓库里没有提交校验脚本。改完文档用一次性 Node 脚本核对下面 5 项不变量——这些是交付验收标准，人工目测查不出来：

```bash
mkdir -p /tmp/evalchk && cd /tmp/evalchk && npm i mermaid jsdom yaml
```

| 检查 | 做法 | 当前基线 |
|---|---|---|
| Mermaid 可渲染 | jsdom + `mermaid.parse()` 逐块解析 md 里的 ` ```mermaid ` 代码块 | 49 块，0 失败 |
| YAML 可解析 | `yaml.parse()` 逐段解析 ` ```yaml ` 代码块 | 20 段，0 失败 |
| **rubric 自身 lint** | 解析出 `task` / `task_group` 的 rubric，按文档自己定的规则复查（见下） | 9 段，0 违规 |
| 链接与锚点 | 提取 `](...)`，校验文件存在 + 标题 slug 存在（**GitHub slug 不折叠连续空格**，`层 × 柱` → `层--柱`） | 224 个，0 失效 |
| 图号与 SVG | `<b>图 X-Y</b>` 图注无重复无断号；`assets/` 无孤儿 SVG | 65 条图注 / 16 个 SVG |

写校验脚本时踩过的三个坑，都会表现成"文档有问题"的假阳性，别照着改文档：

1. **文件是 CRLF。** 切分代码块前先 `.replace(/\r\n/g,'\n')`，否则切出来的片段尾部挂一个孤立 `\r`，YAML 会报 `Implicit map keys need to be followed by map values`。
2. **有些 ` ```yaml ` 块是「坏/好」并排对比**（如 `02` 第 3 节），同一个 fence 里两次 `graders:`，作为单文档解析必然重复键。按 `^#\s*(坏|好)$` 切开分别解析。注意 `\b` 在中文字符后不成立，别用 `好\b`。
3. **`grep`/`glob` 碰中文路径会静默失败。** `grep -r "$k" 智能体评测体系/*.md 2>/dev/null` 在 Git Bash 里 glob 不展开，错误被 `2>/dev/null` 吞掉，结果全是 0 命中。用 Grep 工具，或传绝对路径。

指标条目数不要手写，用 `01` 里的 `^\*\*([A-Z])-(\d{2})\s·` 数（md 基线现为 12 组 **92** 个）。这个数出现在 `01`（两处）、`09` 参考索引共三处，改指标必须三处同步。HTML 增订版里的 **97** 由脚本按 `.mtx` 卡片实际数生成，不手写（= 基线 92 + 本版新增 5）。

