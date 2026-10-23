# 面试 briefing 一致性审计（2026-10-23）

## 目的与范围

把 `docs/interview/briefing/` 三份突击材料收口到当前实现与最新证据：用户在面试前只读这三篇，就能准确讲出项目实现、近期优化、证据、边界与源码定位。本记录是非面试入口的审计留档，不进入突击阅读路径。

基线提交：`83450ef`（分支 `codex/eval-foundation-rebuild`）。

## 只读核验清单（先核验后改写）

| 核验项 | 来源 | 结论 |
|---|---|---|
| 练习模式实现 | `src/agent_mentor/domain/interview.py` → `TrainingMode`；`interview_service.py` → `resolve_training_plan()`；`profile_service.py` → `apply_interview_evaluations()`；`frontend/src/main.jsx`；`frontend/src/components/InterviewPanel.jsx` | profile_training 服务层强制 3 题 / medium；practice 仅 1/3/5 题、三档难度；practice 不写 `QuestionCoverage` / 画像 / ProfileUpdateEvent / ReviewTask，不推进 coverage；`docs/evaluations/practice-mode-verification-20261023.md` |
| 可信 coverage 闭环 | `coverage_catalog.py` → `map_question_coverage()`；`interview_service.py` → `_coverage_source_chunk()`；`docs/evaluations/continuous-coverage-training-20261023.md`；`docs/evaluations/coverage-loop-acceptance-20261022.md` | 目录点须有 source chunk；题目实际引用该来源 chunk 才推进 coverage；连续 6 目标、6/6 source citation、0 重复目标；只证明链路，不证明掌握 |
| 安全目录重索引 | `docs/evaluations/coverage-catalog-safe-reindex-execution-20261023.md`；`docs/evaluations/catalog-reindex-audit-20261023-after.json` | 逐文档、等待 ready、前后审计、不删除历史记录；可信目录点重索引前后均为 99；orphan 96 个仍保留（`orphan_catalog_point_count: 96`），不会被作为可信训练目标 |
| 评分与评测证据 | `docs/evaluations/scoring-stability-panel-20261023.md`；`docs/evaluations/multi-model-blind-calibration-20261023.md`；`docs/evaluations/runtime-and-scoring-stability-baseline-20261022.md`；`docs/acceptance/human-scoring-comparison-contract-v1.md` | 15 次三档模型稳定性观察（low/mid/high 各 5 次）；两模型 12 条 blind 样本 12/12 粗粒度一致；均非人工一致性 / 改判率 / 准确率；尚无真实人工评分金标准 |
| RAG 与失败候选 | `docs/decisions/` ADR-002 / ADR-003 / ADR-004；`src/agent_mentor/config.py` 默认开关 | 失败候选未进入生产默认；未上线 Agent Loop / 真 SSE / LLM tool-calling / 自动切换 Evidence Gate；Embedding 双语境（代码默认 development，标准部署显式启用 BGE，运行态以 `/health/runtime` 为准）；流式为伪流式 |

## 三份 briefing 的修改内容

| 文件 | 修改 |
|---|---|
| `docs/interview/briefing/00-面试突击总览.md` | 更新 30 秒 / 2 分钟话术，明确"正式画像训练 + 隔离自定义练习"两条面试路径；亮点二改为"目录点—真实来源—题目引用—coverage 可验证闭环"，亮点三改为"受控面试工作流与双模式隔离"；边界卡扩为 6 条（新增 practice 不计入统计、多模型一致性≠人工准确率、orphan 保留≠清理失败）；状态表新增双模式与 coverage 来源绑定行；红线卡新增 6 条；主链路图按 `training_mode` 分流；必记数字维持 5 组且全部可回链 |
| `docs/interview/briefing/01-核心链路与源码地图.md` | 新增 §1.1.1"文档 → chunk → catalog point → source link → coverage"链路与铁律、安全重索引真实范围；数据模型图新增 `training_mode` 与 `question_coverage_points`；§3.1 流程改为模式创建；新增 §3.4"正式训练 vs practice"对照表 + practice 源码定位五件套 + 服务层强制理由；§4 增加 practice 只读闸门；§5 症状表新增 4 条（练习影响画像 / coverage 错误推进 / 历史目录点无 source / 默认训练题数难度异常）；导航表与走读顺序同步 |
| `docs/interview/briefing/02-优化决策与追问弹药.md` | 重组为三个主故事（可信 coverage 闭环 / 安全目录治理 / 题数难度隔离为 practice）+ §4 评分证据收口（15 次三档稳定性、两模型 12/12 趋同、无人工金标准、 therefore 不说准确率）；原 Evidence Gate / 检索评测 / 独立验收 / Claim-NLI 压缩为 §5 次级故事摘要（保留决策总表与回链）；追问弹药保留 A–E 并新增 F"覆盖与练习隔离"3 题；附录更新证据索引，新增 2026-10-22/23 报告回链 |

## 历史文档冲突清单

格式：`文件:行号 / 原表述摘要 / 当前事实来源 / 处置`。

| 文件:行号 | 原表述摘要 | 当前事实来源 | 处置 |
|---|---|---|---|
| `docs/interview/AgentMentor 正常面试视角回答.md:222` | "3 题是默认值，可以配置" | `interview_service.py` → `resolve_training_plan()`；`practice-mode-verification-20261023.md` | 已修复=否；已在首部标注历史口径（Q8 整节过期） |
| `docs/interview/AgentMentor 正常面试视角回答.md:230` | "API 的 `question_count` 字段支持 1 到 10 题，用户可以根据自己的时间调整" | 同上；practice 仅 1/3/5 且零画像/coverage 写入 | 已修复=否；已在首部标注历史口径 |
| `docs/interview/AgentMentor 正常面试视角回答.md:245` | "3 题是默认值，不是上限" | 同上（正式训练口径由服务层强制，唯一可比） | 已修复=否；已在首部标注历史口径 |
| `docs/interview/AgentMentor-V2-项目掌握与源码走读手册.md:1704-1716`（原行号，标注后下移 2 行） | 练习四"增加面试题目数量范围校验……合法边界可以完成面试"，暗示任意题数都是合法面试 | `interview_service.py` → `resolve_training_plan()`；`domain/interview.py` → `TrainingMode` | 已修复=否；已在首部标注历史口径 |

## 检查过但判定为一致的项（不修改）

| 文件:行号 | 表述 | 判定 |
|---|---|---|
| `AgentMentor-V2-项目掌握与源码走读手册.md:546,594,1234,1540` | Embedding 双语境（代码默认 development / 部署 BGE / runtime 为准） | 与当前口径一致 |
| `AgentMentor 正常面试视角回答.md:488,495,813`；`AgentMentor-最终工程审计收口.md:260` | 伪流式、真 SSE 为待办 | 与当前实现一致 |
| `AgentMentor-V2-项目掌握与源码走读手册.md:85`；`AgentMentor-两日工程审计与优化复盘.md:309` | 掌握度与覆盖度分离、新增资料不降掌握度 | 仍成立；source-provenance 规则是强化而非推翻 |
| `AgentMentor-面试演示脚本.md:187,227`；`AgentMentor-终局面试展示包.md:35` | "启动三题面试 / 完成三题"演示路径 | 默认训练路径仍成立（按钮文案变为模式相关，流程不变） |
| `agentmentor-v2-interview-qa.md`；`AgentMentor-简历与面试表达总纲.md` | 无题数/难度可调配方；评分表述均带"小样本 / 非人工金标准"边界 | 一致 |
| `AgentMentor-两日工程审计与优化复盘.md:245`；`AgentMentor-V2-面试视角结构化复盘.md:350,384` | "LLM 评分更接近人工标注"但同时声明样本小、不证明准确率 | 与收口后口径一致（未声称人工验证） |

## 明确不做的动作

- 不回写历史验收结论，不把历史计划描述成已实现功能；
- 不删除或大面积重写 `docs/interview/` 下 11 份原始文档（仅在 2 份首部加极短历史口径提示）；
- 不修改任何代码、测试、迁移、数据集与报告原始 JSON；
- 不新增 briefing 第四篇。
