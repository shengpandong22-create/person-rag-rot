# AgentMentor

AgentMentor 是一个面向“Java 后端开发者转向 AI Agent 开发”的个人 AI 面试学习助手。

项目把学习资料放入个人知识库，通过 RAG 提供可追溯回答，再结合可恢复的模拟面试、可信评分、能力画像和复习任务，形成“学习资料 → 问答验证 → 面试训练 → 评分反馈 → 画像更新 → 下一轮复习”的闭环。

核心工程约束：可在 16GB 普通开发机上通过 Docker Compose 本地部署，无需独立 GPU。V1 默认可在无模型 Key 的情况下用本地基线降级运行；配置 DeepSeek/OpenAI-compatible Key 后，会启用真实 LLM 参与 RAG 回答、面试出题和结构化评分。

## 核心能力

- 知识库：支持 Markdown、TXT、PDF、DOCX 上传、解析、分块、去重、版本管理和 pgvector 入库。
- RAG 问答：PostgreSQL 全文检索 + pgvector 向量检索 + RRF 融合，回答携带引用。
- 模拟面试：三题工作流、checkpoint、幂等答案提交、进程重启后可恢复。
- 可信评分：四维评分、Rubric 权重校验、引用白名单、低置信 Reviewer 路由。
- 能力画像：基于可信 Evaluation 更新掌握度、错误模式、复习任务和下一轮训练建议。
- React 前端：提供本地演示工作台，支持知识库恢复、资料上传、RAG 提问和手动答题。

## 当前边界

当前版本已经完成 RAG、工作流、评分、画像和 Docker 本地部署闭环，并提供 OpenAI-compatible LLM Gateway。配置 DeepSeek 示例：

```env
AGENT_MENTOR_LLM_BASE_URL=https://api.deepseek.com/v1
AGENT_MENTOR_LLM_API_KEY=your_api_key
AGENT_MENTOR_LLM_DEFAULT_MODEL=deepseek-chat
```

建议不要把真实 Key 写入仓库；`.env` 已被 `.gitignore` 排除。

如果不配置 Key，系统会自动回退到本地确定性基线，方便测试和离线演示。

## 快速启动

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

访问地址：

- 前端演示：http://localhost:3000
- API 文档：http://localhost:8000/api/v1/docs
- 健康检查：http://localhost:8000/health/ready

查看数据库迁移版本：

```powershell
docker compose exec api alembic current
```

停止服务：

```powershell
docker compose down
```

## 质量检查

Windows 本机 Ruff 可能被应用控制策略拦截，因此推荐在容器中运行 Ruff：

```powershell
docker run --rm -v "D:\AgentStudy\personal-rag-bot:/work" -w /work personal-rag-bot-api sh -c "python -m pip install 'ruff>=0.8,<1.0' >/tmp/ruff-install.log && python -m ruff check src tests migrations frontend/server.py && python -m ruff format --check src tests migrations frontend/server.py"
```

本机类型检查和测试：

```powershell
python -m uv run pyright
python -m uv run pytest
```

前端构建：

```powershell
cd frontend
npm.cmd run build
```

## 文档入口

- [产品与架构设计](docs/design/产品与架构设计.md)
- [Evidence Gate 与 Claim Evaluation 技术设计](docs/design/Evidence-Gate与Claim-Evaluation技术设计.md)
- [Evidence Gate / Claim Evaluation 实验结论](docs/evaluations/evidence-gate-claim-evaluation-20260929.md)
- [RAG 调优方法论与实战复盘](docs/interview/AgentMentor-RAG调优方法论与实战复盘.md)
- [只读 Shadow Agent 设计](docs/design/只读Shadow-Agent设计.md)
- [Shadow Agent Contract Development 结果](docs/evaluations/shadow-agent-contract-development-20261005.md)
- [Shadow Agent 真实模型 Development 结果](docs/evaluations/shadow-agent-semantic-development-20261005.md)
- [Shadow Agent 画像零污染审计结果](docs/evaluations/shadow-agent-zero-write-audit-20261005.md)
- [ADR-004：关闭 Shadow Agent V1 并进入 V2](docs/decisions/ADR-004-关闭ShadowAgentV1并进入V2.md)
- [Relation-Value V3 独立验收结论](docs/evaluations/relation-value-v3-acceptance-20261004.md)
- [ADR-002：关闭 Relation-Value V3 实验线](docs/decisions/ADR-002-关闭RelationValueV3实验线.md)
- [核心 RAG：用户触发二阶段检索](docs/planning/核心RAG下一阶段-用户触发二阶段检索.md)
- [二阶段检索 API 与预算设计](docs/design/用户触发二阶段检索API与预算设计.md)
- [ADR-003：阶段性关闭二阶段检索生产接入](docs/decisions/ADR-003-阶段性关闭二阶段检索生产接入.md)
- [V1 实现规格说明](docs/design/V1实现规格说明.md)
- [V1 分阶段开发计划与验收标准](docs/planning/V1分阶段开发计划与验收标准.md)
- [Phase 6 验收报告](docs/acceptance/phase-6.md)
- [V1 完成状态](docs/V1完成状态.md)
- [本地资源基准](docs/benchmarks/local-resource-v1.md)
- [演示脚本](docs/operations/demo-script-v1.md)
- [简历项目描述](docs/operations/resume-project-v1.md)

## 技术取舍

V1 没有引入 Redis、Celery、Kafka、Elasticsearch、Kubernetes 或本地大模型服务。检索、评分、工作流和画像闭环优先使用 FastAPI + PostgreSQL/pgvector + Docker Compose 完成，目的是把复杂度控制在个人开发机可复现范围内。

前端采用 Vite + React 构建静态产物，Docker 运行阶段复用 Python 轻量镜像提供静态服务和 API 代理，避免额外 Node/Nginx 镜像依赖。
