# Phase 6 验收报告：Web 演示、完整 Compose 与交付收口

## 完成范围

Phase 6 已完成 V1 收口：

- 新增本地演示前端，访问地址 `http://localhost:3000`。
- Docker Compose 增加 `frontend` 服务，与 `api`、`db` 组成完整三服务部署。
- 前端串联知识库、RAG 问答、模拟面试、评分报告、能力画像、复习任务与下一轮训练建议。
- 更新 README，补齐 V1 能力、启动方式、质量检查和文档入口。
- 新增本地资源基准报告、演示脚本和简历项目描述。

## 主要变更文件

- `frontend/index.html`
- `frontend/src/main.js`
- `frontend/src/styles.css`
- `frontend/server.py`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `README.md`
- `docs/benchmarks/local-resource-v1.md`
- `docs/operations/demo-script-v1.md`
- `docs/operations/resume-project-v1.md`

## 自动化验收

已执行：

```powershell
docker run --rm -v "D:\AgentStudy\personal-rag-bot:/work" -w /work personal-rag-bot-api sh -c "python -m pip install 'ruff>=0.8,<1.0' >/tmp/ruff-install.log && python -m ruff check src tests migrations frontend/server.py && python -m ruff format --check src tests migrations frontend/server.py"
python -m uv run pyright
python -m uv run pytest
```

结果：

- Ruff：All checks passed
- Pyright：0 errors, 0 warnings
- Pytest：29 passed

## 容器验收

已执行：

```powershell
docker compose up -d --build
docker compose ps
docker compose exec api alembic current
```

结果：

- `db` healthy
- `api` running
- `frontend` running
- Alembic：`20260719_0006 (head)`

前端访问验收：

```json
{
  "frontend_status": 200,
  "contains_title": true,
  "ready_status": "ok"
}
```

## 资源验收

```text
personal-rag-bot-api-1        84.70MiB / 2GiB
personal-rag-bot-db-1         41.38MiB / 2GiB
personal-rag-bot-frontend-1   19.46MiB / 512MiB
```

完整三服务稳定态约 146MiB，满足 16GB 普通开发机运行约束。

## 技术取舍记录

Phase 6+ 前端增强版使用 Vite + React 构建静态产物，但 Docker 运行阶段复用 `python:3.12-slim` 镜像，通过标准库静态服务和 API 代理运行。

该取舍保留了 React 源码和更好的演示界面，同时避免 Docker Compose 构建阶段依赖 Node/Nginx 基础镜像，符合项目“低成本、可本地复现”的工程约束。

## 退出条件

Phase 6 退出条件已满足：

- V1 可通过 Docker Compose 完整启动。
- 可通过 Web 页面演示核心业务闭环。
- 资源基准、演示脚本和简历项目描述已补齐。
- 全局质量门禁通过。
- 项目可作为简历核心项目进行讲解。
