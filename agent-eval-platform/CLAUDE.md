# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这个工程在哪儿

`agent-eval-platform/` 是 `agent_evaluation` 仓库里唯一的代码工程，外层仓库的主体是一套中文方法论文档（`智能体评测体系/` 十份分册）。两者是**方法论与其落地载体**的关系，不是并列的两个项目：

- 平台里的指标、打分公式、门禁阈值，**权威源都在外层文档**，平台只做消费方。改这些东西要先改文档。
- 外层 `../CLAUDE.md` 管的是文档交付物的规矩（图表约定、引用纪律、跨册同步的数字），跟这里的代码无关，但**涉及指标与公式时以它为准**。
- **两条 tag 命名空间**：文档交付物用 `v1.0.0` / `v2.0.0`，平台用 `platform-v0.1.0`。别把平台的版本打进 `v*`。

## 环境：先看这条，否则会浪费半小时

**这个工程跑不了 Python 3.14。** SQLAlchemy 2.0.36 解析 `str | None` 注解时会崩（`TypeError: descriptor '__getitem__' requires a 'typing.Union' object`），一 import `models.py` 就炸，跟你的改动无关。Dockerfile 用的是 3.11。

本地已经建好一个 3.12 的虚拟环境，**所有 Python 命令都走它**：

```bash
backend/.venv/Scripts/python.exe        # Windows
backend/.venv/bin/python                # Linux/macOS
```

`app/db.py` 在 import 时就 `create_engine(settings.database_url)`，默认指向 PostgreSQL，所以**跑测试必须覆盖 `DATABASE_URL`**，否则会要求装 psycopg2（它在 3.14 上没有 wheel）。

## 常用命令

```bash
# 后端测试（基线 42 项通过）
cd backend && DATABASE_URL="sqlite:///:memory:" .venv/Scripts/python.exe -m pytest tests/ -q

# 单个文件 / 单个用例
... -m pytest tests/test_metric_dict.py -q
... -m pytest tests/test_metric_dict.py::test_sync_inserts_then_is_idempotent -v

# 起后端（前端 vite 代理写死指向 :8000）
cd backend && DATABASE_URL="sqlite:///./dev.db" .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000

# 起前端
cd frontend && npm run dev

# 同步指标字典（幂等，从外层 01 分册解析 92 条）
#   ⚠️ 该脚本已失去依据：原型侧改用 DeepEval 评估器，不再消费 92 条指标字典
cd backend && .venv/Scripts/python.exe -m scripts.sync_metrics [--dry-run]

# 原型交互测试（需先 npm i jsdom）
cd docs && node prototype.smoke.js
```

两个会咬人的地方：

- **vite 只绑 IPv6**。用 `http://localhost:5173` 访问，`127.0.0.1:5173` 连不上。
- **中文路径在 Git Bash 下 glob 会静默失败**。`grep -r "x" 智能体评测体系/*.md 2>/dev/null` 返回 0 命中不代表没有，而是 glob 没展开、错误被吞了。用 Grep 工具或绝对路径。`scripts/sync_metrics.py` 读的正是这样一个路径。

## 架构主线（按需加载）

有几条主线要读多个文件才能拼出来 —— 改摄入 / 评估 / 权限 / schema 之前先
`Skill(ageval-platform-arch)`：摄入有三条写路径但归一化只有一处、处处 fail-open
（改任何一处都要想降级路径）、迁移靠 `ensure_schema()` 没有 Alembic、
评估的两个触发点、权限是两层。
（⚠️ 「指标字典是单向同步的只读实体」一条已随 `prototype-saas-redesign` 作废：评估能力来源改为开源库 **DeepEval** 预置评估器，指标字典屏已从原型删除。`backend/` 的 `metric-dictionary` 能力域与 `scripts/sync_metrics.py` **尚未跟进改造**，见该 change 的交付报告。）

## 改动前必须守住的约定

### 打分公式与几个锁定的数字

```
task_score = s_safety × ( α · s_completion + β · s_robustness )
```

`s_safety` 是 0/1 **乘法门控**——安全违规不能被高完成度抵消。α=0.8 / β=0.2 / τ=0.75 / 默认试次 k=3（关键链路 5）。这些值的权威源在外层 `00-总纲` 与 `01-指标字典`，**代码里改了不算改，要先改文档**。

结果必须同时报 Average / pass@k / pass^k 三个口径。

### `docs/prototype.html` 是界面的事实来源

**20 个导航屏 + 1 个下钻屏**（链路详情）的可点原型，界面的字段名、表格列、页签口径以它为准。改界面的顺序是**先改原型、再改代码**。`docs/prototype.smoke.js` 有 **159 项** jsdom 断言（导航切屏、三切换器、四通道、行下钻、分步表单、三口径、门禁、排序筛选分页、可访问性静态校验），改原型后必须跑通。

### 评估器类型

`models.Evaluator.type` 有 `rule` / `llm` / `agent` / `human` 四种，但 **`agent`（Agent-as-Judge）已被判定建议下线**——评判官不可复现会让评测结论失去仲裁力。`budget.py` 里按 `type in ["llm","agent"]` 处理成本，改动时注意这两个类型是绑在一起的。

## OpenSpec 工作流

这个工程用 OpenSpec 管规划，`.claude/skills/` 下有 6 个技能（propose / apply / update / archive / sync-specs / explore）。

```bash
openspec list                                          # 活跃变更
openspec status --change "<name>"                      # 产物完成度
openspec validate --changes "<name>" --strict          # 严格校验（注意是 --changes 不是 --change）
```

规划产物在 `openspec/changes/<name>/`（proposal → specs → design → tasks 四件），主 spec 在 `openspec/specs/`。**`/openspec-propose` 只产出规划文档，不改代码**；实施要显式走 apply。

## README 里已经过时的地方

`README.md` 内容很全（Docker Compose 启动、演示账号、OTLP 接入细节、运维排障），但有两处与实际不符，别照着做：

- 它说「CI：GitHub Actions(.github/workflows/ci.yml) 自动跑」——**该目录不存在**，没有 CI。
- 它的接入指引按「AgentScope / OpenCode / HTTP API」划分通道，而原型已改为按形态划分的 **LoongSuite 四通道**（Python Agent / Pilot / OTLP 直推 / eBPF 无侵入）。以原型为准。
