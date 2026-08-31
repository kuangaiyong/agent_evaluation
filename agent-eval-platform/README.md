# AgentEval · 智能体评测平台（全自研 MVP）

基于「方案 B · 全自研架构」技术方案与高保真原型实现的 **可运行 MVP 版本**，覆盖核心闭环：
**接入 → 观测（Trace/Session/Turn/Step）→ 评估（在线/离线）→ Bad Case 复核 → 数据集沉淀 → 回归与门禁**。

## 技术栈
| 层 | 选型 |
| --- | --- |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2 + PostgreSQL 16（容器化） |
| 评估引擎 | 自研规则指标 + LLM-as-Judge（OpenAI 兼容 / 内置 Mock 双模式）+ 人工反馈 |
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Vue Router + Axios |
| 部署 | Docker Compose（db / api / web 三服务） |

> 生产演进点（见技术方案 3/4 章）：轨迹存储换 ClickHouse、大载荷换 MinIO、队列换 Kafka/Redis、密码哈希换 argon2
> — 本 MVP 用 PostgreSQL JSONB + 文件卷 + 进程内轮询 Worker 降低落地成本，接口与领域模型保持不变。

## 快速开始
```bash
cd agent-eval-platform
docker compose up -d --build
# 等待构建完成后：
open http://localhost:8088
```

**演示账号**（右上角可切换角色体验权限控制）：
| 账号 | 密码 | 角色 |
| --- | --- | --- |
| lin@corp.com | admin123 | 管理员（全部操作） |
| chen@corp.com | dev123 | 开发（接入/评估/复核） |
| sun@corp.com | ro123 | 只读（写操作置灰） |

**本地开发**：
- 后端：`cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`（需本地 Postgres，或 `docker compose up db`）
- 前端：`cd frontend && npm install && npm run dev`（Vite 代理 /api → 8000）


## OTLP 网关（自研 · 已实现）
AgentScope / OpenCode 等框架通过标准 OpenTelemetry OTLP/HTTP 协议直推平台，网关负责多租户鉴权、字段归一化（Span → Session/Turn/Step）、PII 脱敏与幂等去重。

**端点**：`POST /api/otlp/v1/traces`（Protobuf 与 JSON 双编码；响应同格式）
**鉴权**：请求头 `x-api-key: <应用 API Key>`（OTLP Header 自定义透传）
**AgentScope 接入三步**：
```bash
export OTEL_EXPORTER_OTLP_HEADERS="x-api-key:<API Key>"
# 业务代码仅需 agentscope.init 增加 tracing_url：
#   agentscope.init(project="agent-eval", name="your-agent",
#                   tracing_url="http://<host>:8088/api/otlp/v1/traces")
# Agent.reply 保持 @agentscope.tracing.trace_reply 装饰即可（零业务侵入）
```
**归一化规则**：`invoke_agent` 根 span → Turn；`chat` → LLM Step（入参/出参/Tokens/模型）；`execute_tool` → Tool Step（arguments/result/错误）；`format/embed` 默认跳过（可配 `OTLP_SKIP_SPAN_OPS`）；`gen_ai.conversation.id` → Session（缺省回退 trace_id）；任一 span 异常 → Trace 状态 error。
**其他特性**：手机号/邮箱/身份证自动打码；`otel_trace_id` 唯一去重（exporter 重试不重复）；入库后自动进入在线评估任务与 Bad Case 队列。
**验证脚本**：`docker exec agent-eval-platform-api-1 python scripts/otlp_demo.py`（构造 AgentScope 语义载荷，protobuf/JSON/幂等三通道）。


## 生产化摄入链路（OTel Collector 边车 + Kafka 队列 + 独立 Worker）
```
Agent(OTLP) ──► [OTel Collector :4317/:4318]──► Kafka(agenteval-ingest) ──► [Worker] ──► 归一化/落库/评估
Agent(OTLP) ──► [FastAPI OTLP 网关 :8088/api/otlp]──►(鉴权 x-api-key)──► Kafka ────────────────────┘
```
- **kafka**：Apache Kafka 3.7（KRaft 单节点），主题 `agenteval-ingest`（自动创建）、DLQ `agenteval-ingest-dlq`
- **collector**：OpenTelemetry Collector Contrib 0.113（otlp gRPC/HTTP → Kafka `otlp_proto` 编码），
  应用归属由 Resource 属性 `agenteval.app.id` 决定（SDK 设置 `OTEL_RESOURCE_ATTRIBUTES=agenteval.app.id:<应用ID>`；回退 service.name 名称匹配）
- **worker**：独立消费进程（`python -m app.kafka_worker`），消息异常自动写 DLQ；幂等按 `otel_trace_id` 去重
- **降级**：Kafka 不可用时，FastAPI 网关自动降级为内联处理（开发/单机模式 `KAFKA_BROKERS` 留空即直连）
- 验证：`docker exec agent-eval-platform-api-1 python scripts/otlp_demo.py`（网关路径）
  与 `python scripts/otlp_demo.py` 改发 `http://collector:4318/v1/traces`（Collector 路径，需带 `agenteval.app.id` 资源属性）

## 核心功能（对照原型）
1. **接入中心**：应用 CRUD、API Key 生成/轮换、接入三态（未接入/上报中/已接入/数据中断）、接入引导 Checklist
2. **AI Agent 可观测**：Trace 筛选分页 / 轨迹详情（Turn→Step 树 + Span 入参出参）/ Session 回放
3. **评估器**：规则指标（关键词/正则/JSON Schema/工具成功率）+ LLM-as-Judge（裁判模型/Prompt/标尺）+ 人工反馈；试运行、版本号、Score∈[0,1] 越界拒绝
4. **评估任务**：在线（按应用+采样率+阈值持续评分）/ 离线（数据集批量）；状态机 运行中⇄已暂停→异常→已终止
5. **Bad Case 管理**：阈值自动入队、三选一复核（确认 Bad/误判/待定）、Root Cause 标签、误判率统计、批量复核
6. **数据中心**：轨迹库筛选、三类数据集（评测集/回归集/经典 Case）、上传（JSON/CSV + 行级校验）、被引用禁删
7. **实验与回归**：版本对版本回归实验（坏样本 vs 优质样本对比、退化清单、可发布/不建议发布）
8. **仪表盘**：KPI / Score 趋势 / 低分率 / 应用排行 / 成本 / 评估器雷达 / 异常告警
9. **通知中心**：任务异常/门禁结果/复核到期提醒
10. **系统管理**：三级角色 RBAC、工作空间切换、审计日志

## 数据上报（SDK 侧）
```bash
curl -X POST http://localhost:8000/api/ingest/trace \
  -H "x-api-key: <应用 API Key>" \
  -H "content-type: application/json" \
  -d '{
    "session_id": "s-demo-0001",
    "model": "qwen-plus",
    "version": "v2.4.1",
    "turns": [{
      "role": "user",
      "message": "帮我查一下订单 WX20260821 的物流信息",
      "steps": [{"kind":"tool","name":"search_orders","status":"ok","duration_ms":340},
                {"kind":"llm","name":"生成回复","status":"ok","duration_ms":915,"tokens":356,
                 "output":"您的订单暂未查询到物流信息" }]
    }]
  }'
```
也可用 Python 客户端：`python scripts/ingest_demo.py`（见 backend/scripts）。



## 存储演进：ClickHouse 事件层（双写）
PG 继续承担**控制面与在线查询**（用户/应用/评估器/任务/数据集/复核流）；ClickHouse 承担**事件与分析**：
```
PG 控制面 ──双写──► ClickHouse 事件层
  traces_ch           轨迹事件（TTL 30 天 · 热数据；冷归档 1 年按 TTL 表达式扩展）
  score_records_ch    评分事件（TTL 365 天 · 长周期统计）
  bad_cases_ch        低分事件（TTL 365 天 · 根因分析）
```
- **写路径**：Worker（Kafka 消费）/ OTLP 网关内联 / JSON 直推 三处统一双写（`services/clickhouse_store.py`），失败仅告警不阻断主链路；`ReplacingMergeTree` 保证回填/重放幂等
- **读路径**：仪表盘聚合 **CH-first**（趋势/排行/KPI），查询异常或无数据时自动回退 PG
- **存量回填**：`docker exec agent-eval-platform-api-1 python scripts/backfill_clickhouse.py`
- 未启用（`CLICKHOUSE_ENABLED=false`）自动退化为纯 PG（单机/开发模式）

## 启用真实 LLM-as-Judge（成本保护）
在项目根目录 `.env`（compose 自动加载）配置后重启 api/worker 即生效；留空则用内置 Mock Judge（离线可跑）：
```bash
LLM_API_BASE=https://api.deepseek.com/v1   # OpenAI 兼容裁判端点
LLM_API_KEY=sk-xxx
LLM_JUDGE_MODEL=deepseek-v4-flash
JUDGE_DAILY_LIMIT_YUAN=50                  # 日额度：超额自动暂停关联任务并通知
```
- 每次真实裁判调用按模型单价自动记账（`app/services/budget.py` 定价表），超限后跳过调用并自动暂停使用 LLM/Agent 评估器的在线任务（状态机「异常」+ 通知）
- 模型名不存在时自动回退 Mock Judge（fail-open，不会中断评估）

## CI/CD 质量门禁
回归实验完成后，结论通过 HMAC-SHA256 签名回调 `GATE_WEBHOOK_URL`（请求头 `x-agenteval-signature` / `x-agenteval-event: regression_gate`），送达状态记录在回归报告与「实验与回归→CI/CD 质量门禁」卡片上。本地调试可指向 `http://localhost:8000/api/regression/webhook-echo` 验证签名与载荷。

## 测试
```bash
# 单元测试（评估引擎 / OTLP 网关 / 预算 / 门禁签名）
cd backend && python -m pytest tests -q
# 或容器内：docker exec agent-eval-platform-api-1 python -m pytest tests -q
# CI：GitHub Actions(.github/workflows/ci.yml) 自动跑 后端测试 + 前端构建 + compose 校验
```

## 运维注意事项
1. **重建 api 后必须刷新 nginx 解析**：`docker compose up -d api` 重建容器会变更其 Docker 网络 IP，而 nginx（web 容器）在启动时已缓存 `api` 的旧 IP，导致 502 Bad Gateway（OTLP/API 经由 8088 全部不可用）。
   ```bash
   docker compose restart web        # 让 nginx 重新解析 api 的容器名
   ```
   或一次性重启全部：`docker compose up -d --force-recreate http`（web + api 一起重建，避免该问题）。
2. **api 与 worker 需同步重建**：二者共用 `backend/app` 源码（同一镜像）。后端代码变更后：
   ```bash
   docker compose build api worker && docker compose up -d api worker && docker compose restart web
   ```
3. **Kafka 健康依赖**：kafka 启动较慢（KRaft 单节点约 20–40s）；collector 与 worker 依赖 `service_healthy` 条件，修改 compose 中 kafka 启动配置或健康检查命令后，用 `docker inspect ... -f '{{.State.Health.Status}}'` 确认再启动下游。
4. **队列积压排查**：
   ```bash
   docker exec agent-eval-platform-kafka-1 /opt/kafka/bin/kafka-consumer-groups.sh \
     --bootstrap-server 127.0.0.1:9092 --describe --group agenteval-worker
   # LAG > 0 说明 worker 处理慢或卡住；异常消息落 DLQ 主题 agenteval-ingest-dlq
   ```
5. **数据重置**：`docker compose down -v && docker compose up -d` 会清空数据库与上传目录并重新注入演示种子数据（评估器/任务/轨迹/数据集等），用户/应用数据一并重置。
6. **页面访问端口**：Web 8088（nginx 反代 `/api`→api:8000）、API 直连 8000、OTLP Collector 4317/4318、Kafka 9092（本机调试用，生产不对外）。

## 目录结构
```
agent-eval-platform/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py / config.py / db.py / models.py / schemas.py
│   │   ├── security.py / deps.py / seed.py
│   │   ├── services/ (assembler / evaluators / worker / metrics)
│   │   └── routers/ (auth apps ingest traces evaluators tasks badcases datacenter dashboard regression notifications system)
│   └── Dockerfile / requirements.txt
└── frontend/
    ├── src/ (main.js / api.js / router.js / layout / pages/*)
    └── Dockerfile (nginx 托管 + /api 反代)
```
