# 多 Agent 考试系统 v4.0 — 学习路线图

> **目标**: 用最少的时间掌握项目核心，能自信应对面试
> **原则**: 架构先行 → 核心深入 → 边缘略读 → 面试突击
> **预计时间**: 3-5 天（每天 1-2 小时）

---

## 📊 总览：四阶段学习法

```
┌─────────────────────────────────────────────────────────────┐
│                    学习路线总览                                │
├──────────┬──────────┬───────────┬───────────┬───────────────┤
│ 阶段     │ 内容     │ 时间      │ 代码量    │ 面试覆盖度    │
├──────────┼──────────┼───────────┼───────────┼───────────────┤
│ Phase 1  │ 全局架构 │ Day 1上午 │ ~50行     │ 40% (骨架)    │
│ Phase 2  │ 核心流程 │ Day 1下午 │ ~200行    │ 70% (主流程)  │
│ Phase 3  │ v4.0亮点 │ Day 2     │ ~300行    │ 95% (差异化)  │
│ Phase 4  │ 面试突击 │ Day 3+    │ 按需查阅   │ 100% (实战)   │
└──────────┴──────────┴───────────┴───────────┴───────────────┘
```

---

## 🏗️ Phase 1：全局架构（Day 1 上午，~1小时）

### 目标
能画出架构图，说出每个角色的职责，理解数据流向

### 必读文件（仅3处）

| 序号 | 位置 | 行数 | 必看原因 |
|------|------|------|---------|
| 1 | `multi_agent_exam.py` **L548-597** | ExamState 定义 | **核心！** 理解系统"记忆了什么" |
| 2 | `多Agent考试系统-技术方案.md` **L330-372** | 架构图 + 角色表 | 一张图搞定全局 |
| 3 | `multi_agent_exam.py` **L2361-2434** | CLI 入口 | 了解启动方式和功能全貌 |

### 学习清单（打勾即完成）

```
[ ] 能画出这个流程图:
    用户 → 配置 → 出题 → [手/AI答题] → 批改 → 循环 → 成绩单 → 辅导 → 持久化
    
[ ] 能说出 7 个角色 的职责:
    User / Teacher / Student / Tutor / Persistence / Memory / Tracer
    
[ ] 能解释 Reducer 是什么:
    score: Annotated[int, lambda x, y: x + y]  → 自动累加，不覆盖
    
[ ] 能说出 3 种数据持久化文件:
    exam_history.json / wrong_book.json / student_profile.json
```

### 面试高频问题（Phase 1）

| 问题 | 回答关键词 | 难度 |
|------|-----------|------|
| "介绍一下你的项目" | 3个Agent协作 + HITL + Tool Calling + Memory | ⭐ |
| "StateGraph 的 State 怎么设计的" | TypedDict + Annotated Reducer累加 | ⭐⭐ |
| "为什么用 while 循环而不是 graph.stream()" | 需要在每步后拦截交互(HITL) | ⭐⭐ |

---

## 🔁 Phase 2：核心流程（Day 1 下午，~1.5小时）

### 目标
理解出题→答题→批改→辅导的完整链路，知道每一步怎么实现的

### 必读代码（按顺序读，共 ~200 行）

#### Step 1：初始化 + LLM 创建（必读 ~30行）

```python
# multi_agent_exam.py L686-720 区域
# 搜索 def create_llms
# 重点看: 返回字典有几个 key? 每个 key 对应什么?
```

**关键理解点**：
- 为什么 Teacher 要 2 个 LLM？（普通 + Structured Output）
- Tutor 有几个版本？（普通 + bind_tools 版本）
- temperature 各是多少？为什么不同？

#### Step 2：出题节点（必读 ~40行）

```python
# 搜索 def gen_question_node
# 重点看: with_structured_output(QuestionOutput) 怎么用的
```

**关键理解点**：
- Pydantic SO 是什么？为什么用它？
- 降级策略是什么？（SO 失败 → 正则提取）
- QuestionOutput 模型有哪些字段？

#### Step 3：答题节点（必读 ~30行）

```python
# 搜索 def answer_node
# 重点看: memory 参数怎么注入的
```

**关键理解点**：
- 手动模式和 AI 模式的区别
- AI 学生怎么模拟犯错的？（temperature=0.8 + Memory注入错误模式）

#### Step 4：批改节点（必读 ~30行）

```python
# 搜索 def grade_node  
# 重点看: GradingOutput 结构化输出
```

**关键理解点**：
- 批改也是结构化输出！（和出题一样）
- 返回 grading + feedback 两个字段

#### Step 5：辅导节点 v4（必读 ~70行）⭐⭐⭐ **面试最常问**

```python
# 搜索 def tutor_node_v4
# 这是 v4.0 最大亮点，必须精读!
```

**关键理解点**（按优先级）：

```
优先级1 (必须会说):
  - Tool Calling 三层降级: Tools LLM → 普通 LLM → 默认文本
  - 工具绑定: llm.bind_tools(TUTOR_TOOLS)
  - 工具调用处理: response.tool_calls 遍历执行

优先级2 (加分项):
  - 学生画像参考: profile_manager.load_profile()
  - 短期记忆注入: memory.error_patterns
  
优先级3 (了解即可):
  - Tracer 记录: tracer.record_tool_call()
```

#### Step 6：主循环编排（必读 ~50行）

```python
# 搜索 def run_exam (
# 重点看: while 循环里每一步的顺序
```

**关键理解点**：
- 为什么用 while 而不是 graph.stream？
- 错误模式什么时候记录到 Memory？
- 画像什么时候更新？

### Phase 2 学习检查

```
[ ] 能口述完整流程（不出题看代码）
[ ] 能说出 Structured Output 的 2 个模型（QuestionOutput + GradingOutput）
[ ] 能画出 Tutor Tool Calling 的三层降级图
[ ] 能解释为什么 answer_node 需要 memory 参数
[ ] 能说出 run_exam 中 while 循环的 5 个步骤
```

### 面试高频问题（Phase 2）

| 问题 | 回答关键词 | 难度 |
|------|-----------|------|
| "Structured Output 怎么实现的" | Pydantic BaseModel + .with_structured_output() | ⭐⭐ |
| "如果 LLM 不支持 SO 怎么办" | 正则降级 + _check_supports_structured_output 黑名单 | ⭐⭐⭐ |
| "Tutor 的工具调用过程" | bind_tools → invoke → tool_calls遍历 → 执行 → 结果拼接到回复 | ⭐⭐⭐ |
| "AI学生怎么模拟犯错" | temperature=0.8(高创造性) + Memory注入历史错误模式 | ⭐⭐ |

---

## 🚀 Phase 3：v4.0 四大亮点（Day 2，~2小时）

> **这是你和别人的差异化竞争力！** 面试官最爱问这部分

### 亮点 1：Tool/Function Calling（~45分钟，最重要！）

**必读代码**：

| 位置 | 内容 | 行数 |
|------|------|------|
| 搜索 `@tool` | 3个工具定义 | ~30行 |
| `tutor_node_v4` 函数体 | 工具调用处理逻辑 | ~70行 |
| 搜索 `def _execute_tool_` | 工具执行函数 | ~20行 |

**必须能回答的问题**：

```markdown
Q: 为什么要给 Tutor 加 Tool Calling？
A: v3.0 Tutor 只能被动回答文字。v4.0 让它具备"行动能力"
   → 可以搜索知识库获取权威资料
   → 可以生成针对性练习题
   → 可以分析错误模式
   
Q: 工具调用失败怎么办？
A: 三层优雅降级:
   Level 1: tutor_with_tools.bind_tools() → 完整功能
   Level 2: 普通 tutor_llm.invoke() → 纯对话降级
   Level 3: try/except 捕获异常 → 返回默认文本
   
Q: 工具调用是怎么触发的？
A: 
   1. @tool 装饰器定义 Python 函数
   2. llm.bind_tools([tool1, tool2, ...]) 绑定到 LLM
   3. LLM 返回 response.tool_calls (列表)
   4. 遍历 tool_calls，按 name 分发到对应执行函数
   5. 将工具结果拼接到 explanation 中返回
```

### 亮点 2：Memory 双层记忆（~30分钟）

**必读代码**：

| 位置 | 内容 | 行数 |
|------|------|------|
| 搜索 `class ExamMemory` | 短期记忆模型 | ~15行 |
| 搜索 `class StudentProfile` | 长期画像模型 | ~25行 |
| 搜索 `class StudentProfileManager` | CRUD 操作 | ~30行 |
| `answer_node` 中 memory 注入部分 | 如何使用 | ~20行 |

**必须能回答的问题**：

```markdown
Q: 为什么要双层记忆？
A: 单层不够:
   - 短期(ExamMemory): 同场考试内，错误会累积影响后续题目
   - 长期(StudentProfile): 跨考试持久化，记录学习轨迹
   
Q: 短期记忆怎么影响 AI 学生？
A: answer_node 中:
   1. 从 memory.error_patterns 取最近3个错误
   2. 拼接到 system prompt: "你经常出现XX类型的错误..."
   3. AI 学生看到提示后更可能重复类似错误（更真实）
   
Q: 长期画像什么时候更新？
A: run_exam 结束时:
   1. load_profile() → 加载旧画像
   2. update_from_exam() → 更新统计数据
   3. save_profile() → 持久化到 JSON
   ⚠️ 注意: 不能在update后再load，否则会覆盖! (这是实际踩过的坑)
```

### 亮点 3：Tracer 可观测性（~20分钟）

**必读代码**：

| 位置 | 内容 | 行数 |
|------|------|------|
| 搜索 `class Tracer` | 追踪器主体 | ~60行 |
| 搜索 `class AgentTrace` | 单次记录 dataclass | ~12行 |

**必须能回答的问题**：

```markdown
Q: Tracer 是什么设计模式？
A: AOP (面向切面编程) + 装饰器模式
   类似 Spring 的 @Aspect 或 Python 的 middleware
   
Q: 它追踪了哪些指标？
A: 
   - 延迟 latency_ms (perf_counter 精确计时)
   - 是否成功 success
   - 工具调用次数 tool_calls
   - 错误信息 error_message
   - 按 Agent 维度的聚合统计

Q: 怎么使用的？
A: @tracer.trace("Teacher", "gen_question") 装饰器
   包装任意节点函数，自动记录调用前后状态
```

### 亮点 4：Checkpointer + 优雅降级（~15分钟，了解即可）

**必读代码**：

| 位置 | 内容 | 行数 |
|------|------|------|
| 搜索 `SQLITE_CHECKPOINTER_AVAILABLE` | 兼容性检测 | ~10行 |

**一句话总结**：
> 通过 try-except 动态导入检测环境是否支持 SQLite/Memory Checkpointer，
> 支持则启用状态快照，不支持则静默跳过（不影响核心功能）

---

## 🎯 Phase 4：面试突击（Day 3+，持续迭代）

### 4.1 自我测试：核心问题清单

> **先不看答案，尝试回答以下问题。答不上来的标记为 ⚠️，后面重点补强**

#### 基础题（必须全会）

```
[ ] 你的项目是什么？解决了什么问题？
[ ] 用到了哪些技术栈？为什么选这些？
[ ] LangGraph 和 LangChain 的区别是什么？
[ ] 你的系统有几个 Agent？各自干什么？
[ ] StateGraph 的 State 怎么定义的？Reducer 是什么？
[ ] 什么是 Structured Output？怎么实现的？
[ ] HITL（人机协同）在哪里体现？
[ ] 数据怎么持久化的？用了什么格式？
```

#### 进阶题（v4.0 亮点）

```
[ ] Tool Calling 是什么？你怎么实现的？
[ ] 工具调用失败怎么降级的？（三层降级）
[ ] 双层 Memory 的设计思路？为什么不用单层？
[ ] 学生画像包含哪些信息？什么时候更新？
[ ] Tracer 追踪了什么指标？用什么模式实现的？
[ ] Checkpointer 解决了什么问题？
[ ] 不同 Agent 为什么用不同的 temperature？
```

#### 深入题（展示深度）

```
[ ] 你遇到过最难的技术难题是什么？怎么解决的？
    → 提示: docstring冲突bug / 画像更新被覆盖 / langchain模块路径变更
    
[ ] 如果让你重新设计，你会改进什么？
    → 提示: 异步并发 / SQLite替代JSON / Web UI
    
[ ] 这个项目的扩展性怎么样？怎么加新功能？
    → 提示: 新增Tool / 新增Memory字段 / 新增Agent
```

### 4.2 针对性补强计划

根据自我测试结果，按需深入学习：

#### 如果 ⚠️ Tool Calling 理解不深

```bash
# 补强方案:
1. 重读 tutor_node_v4 完整函数体（逐行理解）
2. 画一张工具调用流程图（手动画，不要看代码）
3. 自己写一个简单的 @tool + bind_tools 例子验证理解
4. 阅读 LangChain 官方文档: Function Calling 章节
```

#### 如果 ⚠️ Memory 机制模糊

```bash
# 补强方案:
1. 运行 python multi_agent_exam.py --profile 查看画像
2. 打开 exam_data/student_profile.json 看实际数据结构
3. 在 answer_node 中加 print(memory.error_patterns) 观察变化
4. 思考: 如果要加一个"学习速度"字段，需要改哪里？
```

#### 如果 ⚠️ 架构讲不清楚

```bash
# 补强方案:
1. 白板/纸上画完整的架构图（不看书）
2. 用自己的话讲给 ChatGPT 听，让它找漏洞
3. 只讲 3 句话版、1 分钟版、5 分钟版三个版本
```

### 4.3 面试黄金回答模板（背熟这段）

> 见技术方案.md **第九章: 面试表述模板**（约 800 字）
> 
> 建议: 不是死记硬背，而是内化为"讲故事"的能力

---

## 📖 附录：代码阅读顺序速查表

### 最小必要阅读（面试够用，总计 ~500行）

```
第1天 上午 (~80行):
  ├── L548-597   ExamState 定义          ★★★★★ 必读
  └── L2361-2434 CLI入口               ★★★★☆ 浏览

第1天 下午 (~250行):
  ├── create_llms()                    ★★★★☆ 理解返回值
  ├── gen_question_node()              ★★★★★ 精读SO用法
  ├── answer_node()                    ★★★★☆ 理解Memory注入
  ├── grade_node()                     ★★★★☆ 精读SO用法
  ├── tutor_node_v4()                 ★★★★★ ★★★★★ 最重要!!
  └── run_exam() while循环             ★★★★★ 理解编排

第2天 (~170行):
  ├── @tool x3                         ★★★★☆ 理解工具定义
  ├── class ExamMemory                 ★★★☆☆ 了解结构
  ├── class StudentProfile             ★★★☆☆ 了解结构
  ├── class StudentProfileManager      ★★★★☆ 理解CRUD
  ├── class Tracer                     ★★★☆☆ 了解装饰器
  └── class AgentTrace                 ★★☆☆☆ 了解dataclass
```

### 可选深入（有时间再看）

```
边缘代码 (~300行, 面试问到的概率 <10%):
  ├── 交互式配置函数 (select_topic/diff/count 等)
  ├── 持久化细节 (save/load JSON)
  ├── 辅助函数 (_classify_error_type 等)
  ├── CLI子命令实现 (--history/--review 等)
  └── Checkpointer 集成代码
```

---

## ✅ 学习完成标志

当你能做到以下几点，就算掌握了这个项目：

```
✅ 能在白板上画出完整架构图（不看书，3分钟内完成）
✅ 能用 3 句话介绍项目（30秒电梯演讲）
✅ 能用 5 分钟详细讲解 v4.0 四大升级
✅ 能现场手写 tutor_node_v4 的伪代码框架
✅ 能回答 "如果让你加一个新 Tool 怎么做"
✅ 能说出至少 2 个开发中遇到的 Bug 及修复过程
✅ 能讲清楚为什么用 while 而不是 graph.stream
```

---

*祝面试顺利！记住：面试官不是要你背诵代码，而是考察你对技术的理解和思考深度。*
