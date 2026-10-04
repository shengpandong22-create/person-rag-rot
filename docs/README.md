# AgentMentor 文档中心

## 1. 阅读顺序

首次了解项目时按以下顺序阅读：

1. [产品与架构设计](design/产品与架构设计.md)：理解项目为什么做、业务闭环和总体技术取舍。
2. [Evidence Gate 与 Claim Evaluation 技术设计](design/Evidence-Gate与Claim-Evaluation技术设计.md)：理解可信回答边界、离线语义评测和生产隔离。
3. [V1 实现规格说明](design/V1实现规格说明.md)：了解数据模型、API、RAG、LangGraph、测试和资源规格。
4. [V1 分阶段开发计划与验收标准](planning/V1分阶段开发计划与验收标准.md)：查看当前开发阶段、任务边界和阶段门禁。
5. `acceptance/phase-N.md`：查看已经完成阶段的真实验收证据。
6. `evaluations/` 与 `benchmarks/`：查看模型效果和工程性能的实测结果。

## 2. 目录结构

```text
docs/
├── README.md                         # 文档总入口与规则
├── design/                           # 稳定的产品、架构和实现规格
│   ├── 产品与架构设计.md
│   └── V1实现规格说明.md
├── planning/                         # 开发阶段、里程碑和验收计划
│   └── V1分阶段开发计划与验收标准.md
├── acceptance/                       # 每个 Phase 完成后的验收记录
│   └── phase-N.md
├── evaluations/                      # RAG、生成和评分效果报告
│   └── <evaluation-name>-vN.md
├── benchmarks/                       # 性能、成本和资源基准
│   └── local-resource-v1.md
├── operations/                       # 部署、配置、排障和演示手册
│   └── <guide-name>.md
└── decisions/                        # 重要架构决策记录 ADR
    └── ADR-NNN-<decision-name>.md
```

评测原始数据集不放在文档目录，统一位于项目根目录的 `evals/datasets/`；`docs/evaluations/` 只保存由数据集产生、便于阅读的报告。

## 3. 分类规则

| 内容 | 存放位置 | 示例 |
|---|---|---|
| 产品目标、系统架构、数据与接口规格 | `design/` | `V1实现规格说明.md` |
| 阶段计划、里程碑、任务边界 | `planning/` | `V1分阶段开发计划与验收标准.md` |
| 阶段完成证据 | `acceptance/` | `phase-0.md` |
| RAG/评分效果报告 | `evaluations/` | `retrieval-baseline-v1.md` |
| 延迟、Token、内存和成本报告 | `benchmarks/` | `local-resource-v1.md` |
| 启动、部署、迁移、排障和演示步骤 | `operations/` | `local-development.md` |
| 影响多个模块的重要技术取舍 | `decisions/` | `ADR-001-use-pgvector.md` |

以下内容不放入 `docs/`：

- 临时草稿和个人笔记。
- 自动化测试源码。
- 评测原始 JSONL 数据。
- 构建产物、日志和临时导出文件。
- 已废弃旧项目的学习说明。

## 4. 命名规则

- 稳定设计：使用清晰中文名称，例如 `产品与架构设计.md`。
- 版本规格：使用版本前缀，例如 `V1实现规格说明.md`。
- 阶段验收：固定为 `phase-0.md` 至 `phase-6.md`。
- 架构决策：固定为 `ADR-NNN-简短名称.md`，编号只增不改。
- 评测和基准：名称包含版本，例如 `retrieval-baseline-v1.md`。
- 不使用“新建文档”“最终版”“最新版”“临时”等无法长期维护的名称。

## 5. 文档变更规则

1. 产品边界和核心技术取舍变化时，先更新 `design/`。
2. 阶段范围或验收标准变化时，同步更新 `planning/`。
3. 完成一个 Phase 后，只在 `acceptance/` 新增真实验收记录，不回写美化历史结果。
4. 重要且难以逆转的技术决策新增 ADR，不仅写在聊天或提交信息中。
5. 测量结果必须来自实际执行，并写明机器、数据规模、命令和时间。
6. 新文档必须从本索引或所属目录 README 链接，避免形成孤立文档。

## 6. 当前权威文档

| 文档 | 状态 | 作用 |
|---|---|---|
| [产品与架构设计](design/产品与架构设计.md) | 已确认 | 产品和总体架构基线 |
| [Evidence Gate 与 Claim Evaluation 技术设计](design/Evidence-Gate与Claim-Evaluation技术设计.md) | 已确认 | 可信 RAG 与 Claim 评测边界 |
| [Evidence Gate / Claim Evaluation 实验结论](evaluations/evidence-gate-claim-evaluation-20260929.md) | 已完成 | 消融、holdout 与拒绝上线证据 |
| [Relation-Value V3 独立验收结论](evaluations/relation-value-v3-acceptance-20261004.md) | 已关闭 | V3 未通过、拒绝生产接入与实验止损 |
| [ADR-002：关闭 Relation-Value V3 实验线](decisions/ADR-002-关闭RelationValueV3实验线.md) | 已接受 | 不创建 V4，资源返回核心 RAG |
| [核心 RAG：用户触发二阶段检索](planning/核心RAG下一阶段-用户触发二阶段检索.md) | 待设计 | 用户可见的扩展召回与新增引用体验 |
| [V1 实现规格说明](design/V1实现规格说明.md) | 已确认 | V1 技术规格基线 |
| [V1 分阶段开发计划与验收标准](planning/V1分阶段开发计划与验收标准.md) | 已确认 | 唯一阶段执行基线 |

当前执行状态：Phase 0 已通过，正在进行 Phase 1（知识库与文档入库）。

下一项工作固定为 Phase 0。Phase 0 完成后，在 `acceptance/phase-0.md` 写入验收结果并更新本索引。
