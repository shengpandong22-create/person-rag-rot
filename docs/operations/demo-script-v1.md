# AgentMentor V1 演示脚本

## 演示目标

用 5-8 分钟展示完整闭环：

```text
资料入库 -> RAG 问答 -> 模拟面试 -> 可信评分 -> 能力画像 -> 复习任务 -> 下一轮训练建议
```

## 演示前准备

```powershell
docker compose up -d --build
```

打开：

- 前端：http://localhost:3000
- API 文档：http://localhost:8000/api/v1/docs

准备一份 Markdown 或 TXT 学习资料，例如 RAG、Spring、HashMap 面试笔记。

## 演示步骤

1. 打开前端首页，说明项目定位：Java 后端转 AI Agent 开发的私人面试学习助手。
2. 点击“创建演示知识库”，上传学习资料。
3. 点击 RAG 问答，展示回答是否有引用，以及证据不足时不会伪造引用。
4. 启动三题模拟面试，连续点击“用示例答案提交”，展示工作流状态推进。
5. 面试完成后生成评分报告和画像，说明总分由应用层计算，不由模型直接决定。
6. 查看能力画像、错误模式和复习任务。
7. 查看下一轮训练推荐，说明画像如何影响后续练习。

## 面试讲解重点

- RAG 前置是为了解决大模型回答无法验证的问题。
- 引用白名单和 Evaluation 引用校验可以避免虚假溯源。
- 工作流 checkpoint 和幂等键让面试流程可恢复、可重试。
- 低置信和争议评分不隐藏，Reviewer 不可用时保留 `review_pending`。
- 画像更新只消费可信 Evaluation，`disputed/review_pending` 不污染画像。
- 整套系统可在 16GB 本地开发机通过 Docker Compose 运行，体现成本控制和工程取舍。
