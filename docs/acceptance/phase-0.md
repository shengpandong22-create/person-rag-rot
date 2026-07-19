# Phase 0 验收记录

## 状态

通过：Phase 0 的代码、静态检查、单元测试、迁移与 Docker Compose 容器验收均已完成。Phase 1 已解锁。

## 完成范围

- 创建 Python 3.12 的 `src/agent_mentor` 分层工程骨架。
- 创建 `pyproject.toml`、Ruff、Pyright、Pytest 和隔离 `.venv` 开发环境。
- 实现 Pydantic Settings、结构化日志、trace ID 和统一 API 错误响应。
- 实现 FastAPI 应用工厂、`/health/live` 与 `/health/ready`。
- 实现 SQLAlchemy 异步引擎、Session 工厂和数据库健康检查。
- 创建 Alembic 初始迁移，启用 pgvector 并创建 `users` 表。
- 定义 LLM、Embedding、Retriever、Repository Transaction Port。
- 实现可记录调用的 Fake LLM、Fake Embedding、Fake Retriever 和内存 User Repository。
- 创建 API、PostgreSQL + pgvector 的 Dockerfile 和 Compose 配置，并限制各服务 2GB 内存。
- 创建 Phase 0 本地开发与验证手册。

## 主要文件

- `pyproject.toml`
- `src/agent_mentor/`
- `migrations/`
- `Dockerfile`
- `docker-compose.yml`
- `docs/operations/phase-0-local-development.md`
- `tests/unit/`

## 已执行的验证

### 质量门禁

```text
python -m ruff check .              → 通过
python -m ruff format --check .     → 通过
python -m pyright                   → 0 errors, 0 warnings
python -m pytest                    → 6 passed
```

测试覆盖：领域层框架隔离、测试环境密钥清除、Fake LLM 调用记录、Fake Embedding 确定性、liveness、readiness 的成功与失败响应。

### Alembic 离线预演

```text
python -m alembic upgrade head --sql → 通过
```

预演 SQL 已确认包含：

- `CREATE EXTENSION IF NOT EXISTS vector`
- `CREATE TABLE users`
- `INSERT INTO alembic_version ('20260718_0001')`

### Compose 静态校验

```text
解析 docker-compose.yml → 通过
```

已确认 Compose 仅声明 `api` 与 `db` 两个服务，且两者均设置 `mem_limit: 2g`。

## Docker Compose 容器验收

Docker Desktop、WSL2 与 Ubuntu 已安装并启动。已成功执行：

```powershell
docker compose up -d --build
docker compose ps
docker compose exec api alembic current
docker compose exec db psql -U agentmentor -d agentmentor -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
```

验证结果：

1. `api` 与 `db` 正常运行，数据库 healthcheck 通过。
2. 两个健康检查均返回 `200`，响应为 `{"status":"ok"}`。
3. Alembic 当前版本为 `20260718_0001 (head)`。
4. `SELECT extname FROM pg_extension WHERE extname = 'vector'` 返回 `vector`。
5. `docker compose restart` 后，迁移版本仍为 `20260718_0001`，两个健康检查继续通过。
6. 运行时实际内存：API 为 `56.37MiB / 2GiB`，PostgreSQL 为 `23.2MiB / 2GiB`。

## 已知限制

- Phase 0 不解析真实文档、不创建业务向量索引、不调用真实 LLM/Embedding。
- 旧 Demo 文件保持原状；Ruff、Pyright 和 Pytest 已明确限定为新工程目录，不扫描旧 Demo。
- 本阶段没有真实数据库在线迁移记录，只有 Alembic 离线 SQL 预演。

## 退出条件判断

| 条件 | 结果 |
|---|---|
| 必需工程交付物存在 | 通过 |
| 自动化质量门禁 | 通过 |
| 离线迁移预演 | 通过 |
| Docker Compose 容器验收 | 通过 |
| 未提前实现 Phase 1 业务 | 通过 |

结论：Phase 0 通过，Phase 1 已解锁。
