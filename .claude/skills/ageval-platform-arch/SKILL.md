---
name: ageval-platform-arch
description: agent-eval-platform 的架构主线（要读多个文件才能拼出来的那几条）：摄入三条写路径但归一化只有一处、处处 fail-open 的降级路径、ensure_schema() 迁移而非 Alembic、评估的两个触发点、两层权限、指标字典是单向同步的只读实体。改摄入 / 评估 / 权限 / schema 之前读这份。
---

## 架构：几条要读多个文件才能拼出来的主线

### 摄入有三条写路径，但归一化只有一处

```
Agent ─OTLP─► Collector :4317/4318 ─► Kafka ─► kafka_worker ─┐
Agent ─OTLP─► FastAPI 网关 /api/otlp/v1/traces ──(鉴权)──────┤─► otlp_gateway.ingest_otel_payload
Agent ─JSON─► /api/ingest/trace ─────────────────────────────┘        └─► clickhouse_store.write_trace_and_events（双写）
```

三条路最终都汇到 `services/otlp_gateway.py` 做 Span → Session/Turn/Step 的归一化，再由 `services/clickhouse_store.py` 双写。**改归一化逻辑只需改一处，但要想到三条路都会走到它。**

### 处处 fail-open，改任何一处都要想降级路径

这套系统的设计主线是「缺什么就退化，不中断主链路」：

| 缺什么 | 退化成什么 | 在哪 |
|---|---|---|
| `KAFKA_BROKERS` 为空或发布失败 | 网关内联处理 | `routers/otlp.py` |
| `CLICKHOUSE_ENABLED=false` 或查询异常 | 纯 PG；仪表盘聚合回退 PG | `services/clickhouse_store.py` / `metrics.py` |
| `LLM_API_KEY` 为空或模型名不存在 | 内置 Mock Judge | `services/evaluators.py` |
| Judge 日额度超限 | 跳过调用 + 自动暂停在线任务 + 通知 | `services/budget.py` |
| ClickHouse 双写失败 | 只告警，不阻断主链路 | `services/clickhouse_store.py` |

加新能力时保持这个风格：**新依赖不可用不能让摄入或评估整体挂掉。**

### 迁移靠 `ensure_schema()`，没有 Alembic

`app/db.py` 的 `ensure_schema()` 是唯一的增量迁移机制。新表由 `Base.metadata.create_all` 建，**给已有表加列必须在 `ADD_COLUMNS` 里补一条**（表名 → `[(列名, 类型)]`），否则存量库不会有那列。

加列走**先查后加**（inspector 查列是否存在 → 发不带 `IF NOT EXISTS` 的 `ALTER TABLE ADD COLUMN`），不用 PG 专有的 `ADD COLUMN IF NOT EXISTS`。这一点有历史教训：早先用 PG 语法且把异常吞在 try/except 里，SQLite 报语法错后静默失效，而测试跑的正是 SQLite，**全绿但迁移从来没生效过**。`tests/test_ensure_schema.py` 就是防它复发的，改这块必须让那四项保持通过。

迁移失败现在记日志不抛出——不该让服务起不来，但也不能无声无息。

### 评估的两个触发点

- **在线**：轨迹入库后立即对 `mode="online" and status="running"` 的任务打分（`routers/otlp.py` → `services.worker.eval_trace_on_tasks`）
- **轮询**：FastAPI lifespan 里 `start_worker()` 起一个进程内 asyncio 循环，按 `AUTO_EVAL_INTERVAL` 扫

### 权限是两层

`deps.py` 里 `current_user`（JWT）→ `current_workspace`（校验 Membership，返回空间内角色）→ `require_write` / `require_admin`。**认证复用组织账号，授权由平台自己存**——所有按空间隔离的查询都要经 `current_workspace` 拿 `ws["id"]` 过滤，漏一处就是跨空间数据泄漏。

### 指标字典是单向同步的只读实体

`services/metric_dict.py` 解析外层 `智能体评测体系/01-指标体系与指标字典.md`，`scripts/sync_metrics.py` 按 `code` 幂等 upsert。三条已经踩过坑的规则：

- **解析器不写死字段标签**。文档里除固定五项（定义/公式/采集/陷阱/阈值）还有 `陷阱一`/`陷阱二`/`实测量级` 这类变体，它们带着 arXiv 出处。未登记标签一律进 `notes` 并保留标签名。`test_no_labelled_bullet_is_dropped` 就是防这个复发的。
- **stale 只报不删**。文档删掉某编号时不自动删行，否则 `evaluators.metric_code` 变成悬空引用。
- **`evaluators.metric_code` 在 DB 上可空**。存量评估器没有映射，置 NOT NULL 会让迁移失败；「必填」在新建/发布路径上拦。

覆盖度 (`coverage()`) **必须传 workspace_id**：字典是全局的，评估器是按空间隔离的，按全局算会让 A 团队看到 B 团队把格子填满。

