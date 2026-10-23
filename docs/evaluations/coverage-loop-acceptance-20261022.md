# 可信查漏补缺：首轮实现验收

## 范围与结论

本次只验证“目录点被选择后，题目是否真的引用其 source chunk 才计为覆盖”。
不重置、不重索引现有用户知识库，也不把旧覆盖数字包装成新规则下的结果。

固定验收资料为 `evals/fixtures/coverage-loop-acceptance-v1.md`；运行器为
`scripts/run_coverage_loop_acceptance.py`，要求至少 3 次独立真实模型生成。

2026-10-22 在隔离知识库上运行 3 次，runtime 为 DeepSeek `deepseek-chat`，三次均为
`generation_mode=llm`，且每一道题的持久化引用均包含目标 `RRF 公式` 的 catalog source
chunk。机器可读原始结果见 `coverage-loop-acceptance-20261022.json`。

这证明的是 source-provenance 门槛，不证明题目质量、评分正确率或用户掌握度。

## 已修复的链路

1. 新建或选择覆盖计划时，API 返回并传递精确的 `coverage_catalog_point_id`。
2. `InterviewService` 选中目标后，将该点真实 source chunk 放入题目引用候选；不再用
   `_ensure_question_coverage` 伪造覆盖映射。
3. 覆盖统计仅接受 `question_references.chunk_id` 与该点
   `knowledge_catalog_sources.chunk_id` 相交的映射。历史不相交记录保留作审计，不能推进状态。
4. 前端把 coverage-gap 计划放在“已入库资料文件名”之前，用户可直接选择；手动改主题则会
   清除目标 ID，避免把自由主题误记为专项查漏。

## 既有库健康审计

对 `AgentMentor BGE 验收知识库` 的只读审计由
`scripts/audit_coverage_health.py` 生成 `coverage-health-audit-20261022.json`。首个快照记录了
112 个 source-backed 点；后续复核发现当前数据库保留 195 个历史 point，其中 96 个已经没有
source link，剩余 99 个 source-backed 点。文档更新时间和 ingestion-job 记录没有显示这 7 份
资料在本次工作期间被重索引，因此不能把这 13 个 link 的变化归因于某一个动作；它已被保留为
运行态异常，后续应以当前 source-backed 快照为准：

| 项目 | 结果 |
| --- | ---: |
| 当前 source-backed 目录点 | 99 |
| 当前未覆盖 | 78 |
| 当前验证中 | 6 |
| 当前已验证 | 15 |
| 首个快照中的历史 coverage 映射 | 503 |
| 首个快照中有真实 source 引用的映射 | 270 |
| 首个快照中引用错配 | 16 |
| 首个快照中缺失引用，不能验证 provenance | 217 |

当前“三题一轮”的实现每轮只安排一个 coverage target，因此逐一访问 78 个未触达点的理论
下界是 78 轮，而非 `ceil(78 / 3)`。这不是 UI 展示问题，而是旧调度策略的容量边界。

## 不在本次结论内

- 目录标题是否都具备最佳教学粒度仍需人工审核；新规则只先剔除确定的演示、图、例子、红线等容器标题。
- 不会因为一次题目或一次高分就宣布掌握；可信评分次数和分数阈值仍由现有规则决定。
- 没有实现题数、难度选择 UI；见设计可行性报告。
