# 本地资源基准：local-resource-v1

## 环境

- 日期：2026-07-19
- 机器约束：16GB 普通开发机，无独立 GPU
- 部署方式：Docker Compose
- 服务：PostgreSQL + pgvector、FastAPI API、Frontend 静态 SPA

## 验收命令

```powershell
docker compose up -d --build
docker compose ps
docker compose exec api alembic current
Invoke-WebRequest http://127.0.0.1:3000/
Invoke-RestMethod http://127.0.0.1:3000/health/ready
docker stats personal-rag-bot-api-1 personal-rag-bot-db-1 personal-rag-bot-frontend-1 --no-stream
```

## 结果

```text
Alembic: 20260719_0006 (head)
Frontend: 200, contains AgentMentor = true
Ready: ok
```

资源快照：

```text
personal-rag-bot-api-1        84.70MiB / 2GiB
personal-rag-bot-db-1         41.38MiB / 2GiB
personal-rag-bot-frontend-1   19.46MiB / 512MiB
```

三服务稳定态总内存约 146MiB，满足 16GB 开发机本地部署约束。

## 说明

Phase 6+ 前端增强版使用 Vite + React 构建静态产物，但 Docker 运行阶段仍复用已可用的 `python:3.12-slim` 基础镜像，通过标准库静态服务和 API 代理运行。

该取舍保留了 React 源码和更好的演示界面，同时避免在 Docker Compose 构建时拉取 Node/Nginx 基础镜像，继续符合“低资源、可复现、低复杂度”的项目约束。
