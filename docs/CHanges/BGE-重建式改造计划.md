# BGE 重建式改造计划

> 目标：将 AgentMentor 当前 development embedding 切换为本地 BGE embedding，提升 RAG 语义检索质量。  
> 改造方式：不做历史向量兼容、不做在线迁移，直接删除旧数据库 volume，重新建库并重新导入资料。  
> 当前决策：历史知识库、chunk、画像、面试记录、报告历史都可以丢弃，后续用新资料重新跑 50 次左右模拟面试验证画像。

---

## 1. 背景与改造动机

当前项目已经跑通了学习训练闭环：

```text
上传资料 → 文档解析/切分 → 向量入库 → RAG 问答 → 模拟面试 → 评分 → 能力画像 → 复习计划
```

但当前 embedding 是 `DevelopmentEmbeddingGateway`，本质是确定性特征哈希。它的优点是轻量、无外部依赖、适合无 Key 测试；缺点是语义能力弱，遇到同义表达、概念相近问题时召回质量上限低。

如果项目要作为 AI Agent / RAG 方向的简历项目，BGE 改造有现实意义：

- 让 RAG 检索从“能跑通”进一步变成“语义上更可信”；
- 能讲清 embedding provider 替换、向量维度变化、数据库重建这些真实工程问题；
- 配合 eval runner，可以形成“改造前后检索质量可评估”的面试材料；
- 更符合中文学习资料和面试资料场景。

这次改造不追求企业级在线迁移，而是采用重建式方案，符合个人项目阶段。

---

## 2. 当前工程现状

### 2.1 已有代码基础

当前代码已经具备以下基础：

```text
src/agent_mentor/ports/embedding_gateway.py
src/agent_mentor/infrastructure/embedding.py
src/agent_mentor/config.py
src/agent_mentor/main.py
src/agent_mentor/application/knowledge_service.py
src/agent_mentor/infrastructure/retriever.py
src/agent_mentor/infrastructure/database/models.py
```

当前调用关系：

```text
KnowledgeService
  ↓
EmbeddingGateway.embed_documents()
  ↓
DevelopmentEmbeddingGateway
  ↓
KnowledgeChunkModel.embedding = Vector(1536)

PostgresHybridRetriever
  ↓
EmbeddingGateway.embed_query()
  ↓
KnowledgeChunkModel.embedding.cosine_distance(query_vector)
```

### 2.2 当前 embedding 配置

当前配置中已有：

```text
embedding_provider
embedding_model
embedding_dimension
embedding_batch_size
```

但 BGE 目前是防误开状态：

```text
EmbeddingProvider.BGE 会直接抛错
embedding_dimension 必须等于当前 pgvector schema 维度 1536
```

这说明项目已经预留了切换点，但还没有真正实现 BGE。

### 2.3 当前数据库维度

当前向量维度写死在：

```text
src/agent_mentor/infrastructure/database/models.py
migrations/versions/20260719_0002_knowledge_ingestion.py
```

当前是：

```text
Vector(1536)
```

BGE-small-zh-v1.5 输出维度是：

```text
512
```

所以这次改造必须将新建库的向量维度改为 512。

---

## 3. 核心决策：重建式改造，不做历史迁移

### 3.1 为什么不做历史迁移

历史迁移意味着：

```text
保留旧知识库
读取所有旧 chunk
用 BGE 重新生成 512 维 embedding
更新数据库字段
处理迁移失败和回滚
兼容迁移期间的新写入
```

这更像企业级在线升级方案，对当前个人项目来说成本偏高。

本项目当前允许删除历史数据，所以采用：

```text
改代码和 schema
删除旧 volume
重新创建数据库
重新上传学习资料
重新跑面试和画像验证
```

### 3.2 面试表达

建议面试时这样讲：

> 我没有做复杂的在线向量迁移，因为这是个人学习训练项目，历史数据可以重建。所以我采用重建式切换：把 pgvector 维度从 1536 调整到 BGE 的 512，清空旧数据库 volume，重新上传资料生成 embedding。这个方案牺牲历史数据兼容，换来实现简单、风险可控、符合项目阶段。

---

## 4. 改造范围

### 4.1 本轮要做

- 新增 `BgeEmbeddingGateway`；
- 引入 `sentence-transformers`；
- 配置支持 `embedding_provider=development|bge`；
- BGE 默认模型使用 `BAAI/bge-small-zh-v1.5`；
- 将新库向量维度调整为 512；
- Docker 挂载 HuggingFace 缓存，避免模型重复下载；
- 更新 `/health/runtime` 展示 provider/model/dimension；
- 删除旧数据库 volume 后重新建库；
- 重新导入 AI Agent / Java 面试资料；
- 跑 RAG、面试、评分、画像闭环；
- 允许用真实 LLM 跑约 50 次模拟面试，验证长期画像是否合理。

### 4.2 本轮不做

- 不做历史数据在线迁移；
- 不做 1536 与 512 双维度兼容；
- 不做多 embedding provider 混存；
- 不做异步重嵌入任务队列；
- 不接 Milvus / Qdrant；
- 不引入 Redis / Celery；
- 不把 BGE 改造成独立 embedding 服务。

---

## 5. 技术设计

### 5.1 目标架构

```text
KnowledgeService
  ↓
EmbeddingGateway
  ├── DevelopmentEmbeddingGateway
  └── BgeEmbeddingGateway
        ↓
     SentenceTransformer("BAAI/bge-small-zh-v1.5")
        ↓
     512 维向量
        ↓
     PostgreSQL + pgvector Vector(512)

PostgresHybridRetriever
  ↓
EmbeddingGateway.embed_query()
  ↓
pgvector cosine_distance()
```

### 5.2 配置设计

建议 `.env` 新增或调整：

```env
AGENT_MENTOR_EMBEDDING_PROVIDER=bge
AGENT_MENTOR_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
AGENT_MENTOR_EMBEDDING_DIMENSION=512
AGENT_MENTOR_EMBEDDING_BATCH_SIZE=16
```

保留 development fallback：

```env
AGENT_MENTOR_EMBEDDING_PROVIDER=development
AGENT_MENTOR_EMBEDDING_DIMENSION=512
```

注意：为了让数据库 schema 单一，本轮重建后默认维度就是 512。即使使用 development provider，也应输出 512 维，避免 provider 切换时维度不一致。

### 5.3 Gateway 设计

新增文件：

```text
src/agent_mentor/infrastructure/bge_embedding.py
```

核心职责：

- 延迟加载或初始化 `SentenceTransformer`；
- 提供 `embed_documents(texts: Sequence[str]) -> list[list[float]]`；
- 提供 `embed_query(text: str) -> list[float]`；
- 对输出向量做维度校验；
- 可选做 normalize embeddings；
- batch size 由配置控制。

建议实现原则：

```text
模型加载一次
批量 encoding
输出 list[float]
维度必须等于 settings.embedding_dimension
异常信息要能说明是模型加载失败、下载失败还是维度不匹配
```

### 5.4 main.py 注入设计

当前 `main.py` 固定：

```text
DevelopmentEmbeddingGateway(settings.embedding_dimension)
```

需要改成：

```text
if settings.embedding_provider == development:
    DevelopmentEmbeddingGateway(settings.embedding_dimension)
elif settings.embedding_provider == bge:
    BgeEmbeddingGateway(model_name=settings.embedding_model, dimension=settings.embedding_dimension, batch_size=...)
```

并保持：

```text
app.state.embedding_provider
app.state.embedding_model
app.state.embedding_dimension
```

用于前端和 `/health/runtime` 观察。

### 5.5 数据库设计

需要修改：

```text
src/agent_mentor/infrastructure/database/models.py
migrations/versions/20260719_0002_knowledge_ingestion.py
```

目标：

```text
KnowledgeChunkModel.embedding = Vector(512)
初始 migration 中 knowledge_chunks.embedding = Vector(512)
HNSW index 保持 cosine ops
```

由于本轮走重建式方案，不需要写复杂 alter migration；但必须保证“空库从 migration 初始化”时就是 512。

如果当前数据库已有旧表，必须执行：

```powershell
docker compose down -v
docker compose up -d --build
docker compose exec api alembic upgrade head
```

### 5.6 Docker 设计

需要关注：

```text
pyproject.toml
Dockerfile
docker-compose.yml
```

建议：

- `pyproject.toml` 增加 `sentence-transformers`；
- Docker 环境变量设置 HuggingFace 缓存目录；
- `docker-compose.yml` 增加模型缓存 volume；
- API 容器挂载缓存，避免每次重建都重新下载模型。

示例设计：

```yaml
services:
  api:
    environment:
      HF_HOME: /cache/huggingface
      TRANSFORMERS_CACHE: /cache/huggingface/transformers
    volumes:
      - hf-cache:/cache/huggingface

volumes:
  hf-cache:
```

是否使用 `TRANSFORMERS_CACHE` 以实际 transformers 版本为准；如果有弃用警告，可以只保留 `HF_HOME`。

---

## 6. 开发步骤

### Step 0：改造前确认

- [ ] 当前 Git 工作区干净，或已提交当前变更；
- [ ] 明确旧数据库 volume 可以删除；
- [ ] `.env` 中 DeepSeek Key 可用；
- [ ] Docker Desktop 内存余量足够；
- [ ] 记录当前测试基线。

建议命令：

```powershell
git status
docker compose ps
docker stats --no-stream
```

### Step 1：新增 BGE 依赖

- [ ] 修改 `pyproject.toml`；
- [ ] 添加 `sentence-transformers`；
- [ ] 本地 `uv sync` 验证依赖能安装；
- [ ] 如果 Windows 本机安装慢，以 Docker 构建验证为主。

验收：

```powershell
python -m uv run python -c "from sentence_transformers import SentenceTransformer; print('ok')"
```

### Step 2：实现 BgeEmbeddingGateway

- [ ] 新增 `src/agent_mentor/infrastructure/bge_embedding.py`；
- [ ] 实现文档 embedding；
- [ ] 实现 query embedding；
- [ ] 增加维度校验；
- [ ] 增加模型加载失败错误说明；
- [ ] 增加单元测试。

建议测试：

```text
同一文本两次 embedding 维度一致
输出维度为 512
空文本或空列表行为明确
batch 多文本能返回等长结果
```

### Step 3：配置与注入改造

- [ ] 修改 `src/agent_mentor/config.py`；
- [ ] 移除 BGE 防误开报错；
- [ ] 默认 provider 可设为 `bge`，也可先保持 `development`，由 `.env` 切换；
- [ ] 修改维度校验逻辑；
- [ ] 修改 `src/agent_mentor/main.py` 注入逻辑；
- [ ] 保持 `/health/runtime` 可展示当前 provider/model/dimension。

推荐策略：

```text
代码默认 development，.env 显式切 bge。
```

理由：

- CI 和无模型环境更稳；
- 面试演示机器通过 `.env` 开启 BGE；
- 没有 HuggingFace 网络时，单测不被模型下载拖死。

### Step 4：pgvector 维度改为 512

- [ ] 修改 ORM model；
- [ ] 修改初始 migration；
- [ ] 检查 HNSW index；
- [ ] 清理所有硬编码 1536；
- [ ] 保留常量，例如 `PGVECTOR_DIMENSION = 512`。

检索命令：

```powershell
rg -n "1536|Vector\\(" src migrations tests
```

### Step 5：Docker 缓存与环境变量

- [ ] 修改 `docker-compose.yml`；
- [ ] 增加 `hf-cache` volume；
- [ ] API 容器设置 `HF_HOME`；
- [ ] `.env.example` 补充 BGE 配置；
- [ ] README 或操作文档补充首次模型下载说明。

### Step 6：删除旧库并重建

这是破坏性步骤。

执行前必须确认：

```text
旧知识库、旧画像、旧面试记录、旧报告都可以删除。
```

命令：

```powershell
docker compose down -v
docker compose up -d --build
docker compose exec api alembic upgrade head
```

验收：

```powershell
docker compose logs api --tail 200
```

确认无：

```text
expected 512 dimensions, not 1536
expected 1536 dimensions, not 512
```

### Step 7：重新导入资料

建议重新建立两个知识库：

```text
AI Agent 开发面试知识库
Java 后端面试知识库
```

建议资料分组：

```text
AI Agent:
- RAG.md
- LangGraph.md
- LangChain.md
- Memory.md
- Evaluation.md
- Tool Calling.md

Java:
- JVM.md
- 并发.md
- Spring.md
- MySQL.md
- Redis.md
- 微服务.md
```

验收：

- [ ] 所有文档状态为 ready；
- [ ] chunk 数量合理；
- [ ] coverage catalog 能生成；
- [ ] 页面刷新后知识库可恢复。

### Step 8：RAG 与检索评估

先跑人工问题：

```text
RAG 为什么需要引用溯源？
LangGraph checkpoint 和普通缓存有什么区别？
Agent Memory 和普通数据库记录有什么区别？
HashMap 扩容机制是什么？
Spring 事务失效有哪些场景？
```

再跑 eval runner：

```powershell
python -m uv run python -m evals.run retrieval --knowledge-base-id <kb_id>
```

验收：

- [ ] RAG 返回内容与知识库相关；
- [ ] citation 存在；
- [ ] 不相关问题触发边界提示或明显低证据；
- [ ] eval report 生成；
- [ ] 指标记录到 `docs/evaluations/`。

### Step 9：50 次面试画像验证

用户已允许跑大约 50 次 LLM 交互/面试流程。

建议不要一次混跑，而是分组：

```text
AI Agent 知识库：30 次
Java 后端知识库：20 次
```

或者：

```text
AI Agent:
- RAG 10 次
- LangGraph 8 次
- Memory 6 次
- Evaluation 6 次

Java:
- JVM 5 次
- 并发 5 次
- Spring 5 次
- MySQL/Redis 5 次
```

验证目标：

- [ ] 题目是否基于对应知识库；
- [ ] 题目是否有随机性，不总是同一道；
- [ ] 覆盖保底策略是否能触发未覆盖知识点；
- [ ] 高分后画像是否渐进上升；
- [ ] 连续高分是否关闭对应复习任务；
- [ ] 不同知识库画像是否隔离；
- [ ] Java 知识库不会污染 Agent 知识库画像；
- [ ] 报告历史能记录多轮趋势。

输出报告：

```text
docs/evaluations/bge-profile-validation-YYYYMMDD.md
```

报告至少包含：

```text
环境信息
知识库信息
导入文档清单
RAG 抽样问答结果
50 次面试分布
画像变化截图或数据
复习任务变化
发现的问题
后续建议
```

---

## 7. 验收标准

### 7.1 代码验收

- [ ] `pytest` 全部通过；
- [ ] `pyright` 通过；
- [ ] `ruff check .` 通过；
- [ ] `rg -n "1536|Vector\\(" src migrations tests` 无不合理残留；
- [ ] `BgeEmbeddingGateway` 有单元测试；
- [ ] `DevelopmentEmbeddingGateway` fallback 仍可用。

### 7.2 Docker 验收

- [ ] `docker compose up -d --build` 成功；
- [ ] API 容器能加载 BGE 模型；
- [ ] HuggingFace cache volume 生效；
- [ ] 重启容器后不重复下载模型；
- [ ] `/health/runtime` 显示：

```json
{
  "embedding_provider": "bge",
  "embedding_model": "BAAI/bge-small-zh-v1.5",
  "embedding_dimension": 512
}
```

### 7.3 入库验收

- [ ] 新建知识库成功；
- [ ] 上传 Markdown/TXT/PDF/DOCX 至少一种成功；
- [ ] 文档状态进入 `ready`；
- [ ] chunk embedding 写入成功；
- [ ] 无维度不匹配错误。

### 7.4 RAG 验收

- [ ] 与资料相关的问题能召回相关片段；
- [ ] 回答带 citation；
- [ ] citation chunk_id 在候选白名单内；
- [ ] 不相关问题不会强行伪装成资料结论；
- [ ] eval runner 能输出报告。

### 7.5 面试闭环验收

- [ ] 能完成一轮三题面试；
- [ ] 题目基于知识库内容；
- [ ] 默认参考答案由 LLM 或 fallback 生成；
- [ ] 用户回答能提交；
- [ ] 评分报告能生成；
- [ ] 能力画像能更新；
- [ ] 复习任务能生成或关闭；
- [ ] 报告历史能展示趋势。

### 7.6 50 次画像验证验收

- [ ] 至少两个知识库分别跑完整面试；
- [ ] 面试主题分布覆盖 RAG、LangGraph、Memory、Evaluation、Java 后端等；
- [ ] 画像与知识库隔离；
- [ ] 连续高分主题画像有上升趋势；
- [ ] 低分或缺失主题进入复习任务；
- [ ] 未覆盖知识点能被覆盖保底策略逐步考到；
- [ ] 形成验证报告。

---

## 8. 风险与回滚

### 8.1 主要风险

| 风险 | 表现 | 应对 |
|---|---|---|
| HuggingFace 下载失败 | Docker build 或首次启动卡住 | 使用 HF cache；必要时手动下载模型 |
| 依赖过重 | build 慢、镜像大 | 只用 small 模型；不引入本地大模型 |
| 维度不一致 | 写入 pgvector 报错 | 统一常量 512；全局搜索 1536 |
| 内存不足 | API 容器 OOM | 降低 batch size；保留 development fallback |
| 检索效果不如预期 | RAG 召回仍不准 | 用 eval runner 调 chunk 和 query |
| 画像验证耗时 | 50 次 LLM 交互时间长 | 分批跑，先 10 次 smoke，再扩到 50 次 |

### 8.2 回滚方式

如果 BGE 改造失败，回滚代码：

```powershell
git restore .
```

或切回上一 commit。

如果数据库已经清空：

```text
旧数据不可恢复，除非提前做 pg_dump。
```

虽然用户明确允许不要历史数据，但执行前仍建议备份一次：

```powershell
docker compose exec db pg_dump -U agentmentor agentmentor > backups/before-bge-rebuild.dump
```

这是低成本保险。

---

## 9. 面试讲法

### 9.1 30 秒版本

> 项目早期为了保证本地可运行，用 development embedding 跑通了 RAG 和面试闭环。后面为了提升中文资料的语义召回质量，我切换到 BGE-small-zh-v1.5。因为这是个人学习项目，历史数据可以重建，所以我没有做复杂在线迁移，而是采用重建式方案：把 pgvector 维度改为 512，清空旧库，重新上传资料生成新 embedding，并通过 RAG 问答、eval runner 和多轮面试画像验证效果。

### 9.2 90 秒版本

> 这个改造的重点不是简单“换个模型”，而是处理 embedding 变更带来的工程问题。原来 development embedding 是 1536 维特征哈希，轻量但语义能力弱；BGE-small-zh 是 512 维真实中文 embedding，所以数据库向量字段、配置、入库、检索和健康检查都要一起调整。  
>  
> 我没有做在线历史迁移，因为当前项目是个人学习训练场景，历史知识库和画像可以重新生成。这样我选择了重建式切换：删除旧 volume，重新初始化 schema，重新上传 AI Agent 和 Java 面试资料。这个方案的好处是复杂度低、失败成本可控；代价是历史数据不保留。  
>  
> 改造后，我会通过三层验证：第一是代码和 Docker 验收，确保 BGE provider、512 维向量和 pgvector 写入正常；第二是 RAG 问答和 retrieval eval，确认召回质量；第三是跑多轮模拟面试，看能力画像、复习任务和知识库隔离是否正常。

### 9.3 面试官追问：为什么不做历史迁移？

答：

> 在线迁移适合已有用户和历史数据不能丢的产品。但这个项目当前是个人学习场景，数据可重建，所以我选择低风险的重建式迁移。这个取舍不是不会迁移，而是按项目阶段控制复杂度。如果未来有真实用户，就需要做双写、索引版本、后台重嵌入和灰度切换。

### 9.4 面试官追问：为什么选 bge-small-zh？

答：

> 因为项目资料主要是中文技术学习资料和面试问答，BGE 中文 small 模型在效果、体积和本地资源之间比较平衡。我的机器是 16GB，Docker 分配约 6GB 多内存，所以不适合直接上更大的 embedding 模型。small 模型能在本地 CPU 环境下完成语义 embedding，同时不会破坏 Docker Compose 本地部署约束。

### 9.5 面试官追问：怎么证明 BGE 真的提升了？

答：

> 我不会只凭主观感觉说提升。项目里有 retrieval eval runner，可以用固定 query 和 expected keywords 计算 Recall@1/3/6、MRR、证据充分率等指标。改造前后用同一批数据跑一遍，就能形成对比。除此之外，我还会用多轮模拟面试观察题目是否更贴合知识库、画像是否更合理。

---

## 10. 执行顺序建议

建议分三次提交，避免一次改太多。

### Commit 1：BGE Gateway 与配置

```text
新增 BgeEmbeddingGateway
配置 provider 注入
单元测试
```

建议提交信息：

```text
feat(embedding): add bge gateway with provider switch
```

### Commit 2：512 维 schema 与 Docker 缓存

```text
Vector(1536) → Vector(512)
初始 migration 同步
docker-compose 增加 HF cache
.env.example 更新
```

建议提交信息：

```text
feat(embedding): rebuild vector schema for bge dimension
```

### Commit 3：重建验收与报告

```text
清空旧库
重新导入资料
RAG/面试/画像验证
输出验证报告
```

建议提交信息：

```text
docs(eval): record bge rebuild validation results
```

---

## 11. 开工前最终确认

执行代码改造前，需要再次确认：

- [ ] 用户接受删除旧数据库 volume；
- [ ] 用户接受旧知识库、画像、面试历史、报告历史全部丢弃；
- [ ] 用户接受首次 BGE 模型下载可能较慢；
- [ ] 用户接受 Docker 镜像变大；
- [ ] 用户允许运行 Docker 重建；
- [ ] 用户允许使用 DeepSeek Key 跑约 50 次 LLM 面试验证；
- [ ] 用户接受如果 BGE 遇到网络/依赖问题，可以临时切回 development provider。

当前用户已明确：

```text
历史数据可以不要，重新导入资料即可。
允许跑大约 50 次面试流程（LLM 交互），生成个人画像验证。
```

因此，本计划确认后即可进入代码改造阶段。
