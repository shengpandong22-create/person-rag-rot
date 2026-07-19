# 简历项目描述：AgentMentor

## 一句话描述

AgentMentor 是一个面向 Java 后端转 AI Agent 开发的个人 AI 面试学习助手，支持资料入库、RAG 问答、可恢复模拟面试、可信评分、能力画像和复习任务闭环。

## 简历写法

独立设计并实现 AgentMentor AI 面试学习助手，面向 Java 后端开发者转型 AI Agent 开发场景，基于 FastAPI、PostgreSQL/pgvector 与 Docker Compose 构建可在 16GB 普通开发机运行的本地系统。项目实现了文档解析与向量入库、全文+向量混合检索、带引用 RAG 问答、可 checkpoint 恢复的模拟面试工作流、Rubric 四维可信评分、低置信复核路由、能力画像和复习任务闭环，并提供完整本地演示界面与阶段验收报告。

## 可量化亮点

- 支持 Markdown、TXT、PDF、DOCX 四类资料解析入库。
- 使用 PostgreSQL 全文检索 + pgvector 向量检索 + RRF 融合，避免单一路径召回偏差。
- 评分输出包含四维分数、覆盖点、缺失点、错误论断、引用 chunk 和置信度。
- 应用层计算总分，避免模型直接决定最终分数。
- Reviewer 不可用时显式标记 `review_pending`，不伪造复核完成。
- `disputed/review_pending` 不更新能力画像，避免低可信结果污染学习闭环。
- Docker Compose 三服务稳定态内存约 146MiB，满足 16GB 开发机部署约束。

## 面试可讲技术点

- RAG 可信边界：为什么检索、引用、证据不足降级是必要的。
- Agent 工作流：如何用 checkpoint 和幂等键保证中断恢复。
- 评分可信性：Rubric、引用白名单、应用层总分、Reviewer 路由。
- 画像闭环：如何从 Evaluation 转为复习任务和下一轮训练建议。
- 工程取舍：为什么 V1 不引入 Kafka、Redis、ES、K8s 或独立向量数据库。
