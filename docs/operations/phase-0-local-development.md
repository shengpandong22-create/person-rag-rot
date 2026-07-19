# Phase 0 本地开发与验证

## 前置条件

- Python 3.12
- Docker Desktop（启用 Linux containers / WSL2）
- Docker Compose v2

推荐为 Docker Desktop/WSL2 分配 4～6GB 内存。Phase 0 只有 API 与 PostgreSQL + pgvector 两个服务，每个服务的 Compose 内存上限均为 2GB。

## 启动

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
```

## 验证

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
docker compose exec api alembic current
docker compose exec db psql -U agentmentor -d agentmentor -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

预期：两个健康检查都返回 `status: ok`，Alembic 指向 `20260718_0001`，查询返回 `vector` 扩展。

## 本地质量检查

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pyright
python -m pytest
```

## 常见问题

- Docker 不在 PATH：启动 Docker Desktop 后重新打开 PowerShell。
- `ready` 返回 503：检查 `docker compose ps`、数据库 healthcheck 和 `.env` 中数据库地址。
- 端口冲突：修改宿主机端口映射，不修改容器内部的 `db:5432` 地址。
- 无法执行 Python：确认 Python 3.12 已加入 PATH，或使用其绝对路径创建虚拟环境。
