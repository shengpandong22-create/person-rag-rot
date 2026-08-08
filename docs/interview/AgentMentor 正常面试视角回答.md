# AgentMentor 正常面试视角回答（高分拓展版）

> 目标：4.2 / 5 的面试表现  
> 策略：用“技术聊天”的方式讲故事，每个问题提供 30 秒简短版 + 90 秒深入版 + 追问防御 + 质疑应对。

---

## 面试表达总则

### 三个原则
1. **先给结论，再给细节**：面试官 10 秒没听到重点会走神
2. **用一个例子贯穿**：把抽象设计落到具体场景
3. **诚实但有框架**：对未完成的部分，用“这是 V1 边界，我的修复计划是 X”替代“没做”

### 推荐节奏
- 开场介绍：90-120 秒
- 每个主问题：30-60 秒简短版，面试官感兴趣再展开到 90 秒
- 每个追问：20-40 秒

---

## 第一部分：开场与项目理解

### Q1：AgentMentor 解决的核心问题是什么？

#### 30 秒简短版
AgentMentor 是一个面向 Java 后端转 AI Agent 的面试学习助手。它解决三个问题：资料分散复习难、通用工具出题不针对、错题能力没有沉淀。核心是把“上传资料 → RAG 问答 → 模拟面试 → 评分 → 能力画像 → 复习任务”串成闭环。

#### 90 秒深入版
我自己就是目标用户。去年开始转 AI Agent 时，我发现学习资料散落在 PDF、博客、笔记里，复习时不知道从哪里开始。ChatGPT 能回答问题，但有两个问题：第一，它不会基于我上传的《某大厂 RAG 实践.pdf》出题；第二，每次对话都是从头开始，我之前哪里错了、哪类题不擅长，没有沉淀。

所以 AgentMentor 的设计目标是：**让面试准备过程可追踪、可复盘**。闭环是：上传资料 → 用 RAG 验证理解 → 模拟面试 → 按 Rubric 评分 → 更新能力画像 → 生成复习任务 → 下一轮面试针对性补强。

#### 追问防御

**Q1.1：你自己就是这个目标用户吗？**
是的。最具体的触发场景是：我上传了一份 RAG 相关的学习笔记，想让系统基于这份笔记出题考我，但发现通用工具要么出得很泛，要么不校验引用是否来自我的笔记。这让我觉得需要一个“以我的资料为边界”的面试训练工具。

**Q1.2：三者关系是什么？缺一不可吗？**
可恢复面试是入口，可信评分是质量保障，能力画像是长期价值。从闭环完整性讲缺一不可，但如果是 MVP，可以先有前两个，画像可以后补。V1 其实是把三个都做了，但画像展示还比较基础。

**Q1.3：对不懂技术的 HR 怎么说？**
AgentMentor 就像一个私人面试教练。你上传自己的学习资料，它自动从中出题、给你打分，并告诉你“RAG 检索这部分你掌握得还不够，建议复习这三个知识点”。

#### 质疑应对
**质疑：这不就是 ChatGPT + 上传文件吗？**
ChatGPT 能问答，但它不会为后端转 Agent 这个人群设计四类题型和 Rubric，不会在评分时校验引用是否来自你的资料，也不会把错题模式沉淀成可追踪的画像。AgentMentor 不是问答工具，是学习系统。

---

### Q2：为什么特别强调 16GB 和无 GPU？

#### 30 秒简短版
这个约束来自我自己的机器配置，也是目标用户的典型环境。身边后端同事大多是 16GB MacBook 或 Windows 笔记本，没有 GPU。这个约束直接决定了：不用本地大模型、用 PostgreSQL+pgvector 而不是独立向量库、用 Docker Compose 而不是 K8s。

#### 90 秒深入版
16GB 和无 GPU 是我给自己设的工程约束。原因有两个：一是我自己机器就是 16GB；二是我不想做一个需要用户升级硬件才能用的工具。

这个约束直接影响了选型：
- **不用本地大模型**：7B 模型虽然能跑，但会挤占 PostgreSQL 和前端服务的内存，体验很差，所以 V1 调用远程 LLM API；
- **用 PostgreSQL + pgvector**：避免再引入 Milvus、Qdrant 这类专门向量库，减少部署复杂度；
- **用 Docker Compose**：单机低并发场景下完全够用；
- **设计无 Key 降级**：让没有 API Key 的用户也能在本地跑通流程，虽然质量会下降。

#### 追问防御

**Q2.1：没有这个约束会怎么选？**
可能会引入 Ollama/vLLM 跑本地模型降低长期成本，用专门向量数据库或 Elasticsearch，引入 Redis 做缓存和 Celery 做异步任务，部署上可能用 Kubernetes。但 V1 的核心目标是“个人开发机可复现”，所以做了减法。

**Q2.2：这个约束有没有让你错过更好的方案？**
有。比如 pgvector 在大规模数据下不如专门向量数据库，但 V1 的评估是：个人用户几万到几十万条 chunk 的场景，pgvector 够用。等数据量上来再拆，而不是一开始就把架构搞重。

#### 质疑应对
**质疑：为了本地跑而牺牲扩展性，是不是短视？**
我觉得这是有意识的 trade-off。V1 的目标是验证“后端转 Agent”这个学习闭环是否成立。如果一开始就引入 K8s、Kafka、Redis，个人用户根本跑不起来，我也就无法快速迭代。扩展性是 V2 的问题。

---

## 第二部分：RAG 与可信边界

### Q3：为什么不是只用向量检索？

#### 30 秒简短版
因为向量检索和全文检索擅长召回不同类型的内容。向量检索适合“语义相似但关键词不同”，全文检索适合“精确术语匹配”。只用一路会漏掉很多正确答案，所以用 RRF 融合两路排名。

#### 90 秒深入版
举两个例子就明白了。

用户问“怎么减少检索时的幻觉”，向量检索能召回讲 citation、grounding、faithfulness 的 chunk，即使用户没提这些词。这是向量的优势。

但用户问“RRF 的 k 值是多少”，全文检索更可能召回正确结果，因为这是一个术语精确匹配的问题。向量检索可能会召回语义相关但不含具体 k 值的 chunk。

所以我把两路结合起来，用 RRF 把排名转换成可比较的分数再相加。这样语义相关和术语精确的 chunk 都有机会排到前面。

#### 追问防御

**Q3.1：RRF 用一句话解释？**
把两路检索的排名转换成“第几名得多少分”，然后相加，让双路都认可的候选胜出，但只被一路看好的候选也有机会进入 top_k。

**Q3.2：遇到过两路冲突吗？**
遇到过。比如向量检索把讲“语义检索”的 chunk 排得很高，全文检索把讲“RRF 公式”的 chunk 排得很高。RRF 的处理方式是：两路都排第 1 的候选得分最高；只有一路排得高的候选仍然有机会，但会输给双路都认可的。这样不会完全压制某一路的独特结果。

**Q3.3：如果用户问得很模糊，两路都召回不准怎么办？**
这就是 `evidence_guard` 的作用。如果 top chunk 的 RRF 分数低于阈值，系统拒绝回答或明确降级为模型常识回答，不强行编造。

#### 质疑应对
**质疑：混合检索是不是过度工程？单用向量不行吗？**
单用向量在精确术语匹配上容易丢答案。面试场景里用户经常问具体概念、类名、公式，比如“RRF 的 k 值”、“SQLAlchemy 的 selectinload 怎么用”。全文检索对这种问题更稳。两路融合的成本只是一次额外查询，收益很大。

---

### Q4：带引用 RAG 问答有多重要？

#### 30 秒简短版
引用是这个项目“可信”的核心。没有引用，RAG 就退化成普通 LLM 问答，无法区分答案来自用户资料还是模型幻觉。面试评分如果基于幻觉答案，会误判用户水平。

#### 90 秒深入版
引用解决三个问题：
1. **幻觉**：LLM 可能把通用知识和用户资料混在一起，用户无法判断；
2. **不可溯源**：用户想回看原文，找不到出处；
3. **评分失真**：面试评分如果基于编造答案，会误判用户水平。

我们的机制是：LLM 在生成答案时自己决定引用哪些 chunk_id，但系统会强制要求引用必须来自本次检索到的白名单。生成后还会做白名单校验和词法关联校验。

#### 追问防御

**Q4.1：如果 LLM 引用了一个相关但不是答案来源的 chunk，能发现吗？**
能部分发现。白名单校验拦截“编造 chunk_id”，词法关联校验要求 chunk 与问题有术语重叠。但如果 chunk 真的相关、只是 LLM 对内容解读错了，目前拦不住。V2 需要引入“引用内容必须与答案主张一致”的语义校验。

**Q4.2：如果资料里没有答案怎么办？**
触发 `evidence_guard`。默认拒绝回答并提示“当前知识库证据不足”；如果配置允许，会进入 LLM 生成并明确标注“模型补充”。

#### 质疑应对
**质疑：引用校验会不会让系统太保守，经常拒答？**
当前阈值其实设得很低（0.01），基本不会误拒。V2 我会用 eval 集画 ROC 曲线，选择误拒率 <5% 下的最低阈值。可信比“总是回答”更重要，尤其是在面试训练场景。

---

### Q5：“证据不足降级”是什么意思？能举个例子吗？

#### 30 秒简短版
当检索到的 chunk 与问题相关性很低时，系统不强行让 LLM 基于资料编造答案，而是拒绝回答或明确降级为模型常识回答。

#### 90 秒深入版
举例：用户问“深圳明天天气怎么样”。系统检索到的 chunk 都是关于 RAG、Java 并发之类的面试资料，和天气无关。此时 top chunk 的 RRF 分数会很低，触发证据不足。

默认行为是拒绝回答，返回“当前知识库证据不足，我不能把模型常识伪装成资料结论”。如果开启 `allow_model_knowledge=True`，会用 LLM 通用知识回答，但会明确标注“模型补充”，让用户知道这不是来自他的资料。

#### 追问防御

**Q5.1：怎么避免过度拒绝？**
用 eval 集里的正例和负例画 ROC：横轴是正例被错误拒绝的比例，纵轴是负例被正确拒绝的比例，选择误拒率可接受（比如 <5%）下的最低阈值。当前 0.01 是占位值，V2 会正式调参。

**Q5.2：用户会不会觉得系统老是不回答，体验不好？**
会。所以 V2 应该补充两个体验优化：一是拒绝时引导用户上传相关资料；二是提供“用模型常识回答一次”的显式按钮，而不是默认开启或完全拒绝。

#### 质疑应对
**质疑：直接让 LLM 回答不就行了，用户不关心答案来自哪里？**
在面试训练场景，用户很关心答案是否来自他的资料。如果系统用模型常识回答了一个用户资料里没有的知识点，用户会误以为这个知识点不需要补，从而漏掉薄弱点。可信边界是 AgentMentor 的核心卖点。

---

## 第三部分：Agent 工作流

### Q6：checkpoint 是在什么情况下用的？

#### 30 秒简短版
checkpoint 有两个用途：一是记录面试流程中每个节点的状态变化，方便排查问题；二是理论上支持恢复。但 V1 只实现了持久化，还没有实现完整的自动恢复逻辑。

#### 90 秒深入版
面试流程有多个节点：加载画像、规划面试、生成题目、等待答案、评分、完成。每次节点推进，系统会把当前状态写入 PostgreSQL 的 `workflow_checkpoints` 表。

这个设计有两个价值：
1. **可观测性**：如果面试出现状态不一致，可以通过 checkpoint 历史追溯原因；
2. **可恢复性**：为进程重启后的恢复提供数据基础。

但 V1 只实现了持久化，**自动恢复逻辑还没做完**。进程重启后，面试依赖 `InterviewSessionModel` 的当前状态，而不是从最新 checkpoint 恢复。

#### 追问防御

**Q6.1：用户答到一半服务器挂了怎么办？**
恢复后他看到的状态取决于崩溃时机。如果崩溃发生在答案写入之后、状态更新之前，可能会出现 `current_question_index` 已经增加但 `status` 还是 WAITING_FOR_ANSWER 的不一致。V1 没有回滚机制，这是已知边界。V2 会把状态更新合并到同一个事务，并补 checkpoint 恢复逻辑。

**Q6.2：checkpoint 和幂等是什么关系？**
两者正交。checkpoint 记录流程状态，幂等保证同一个答案不会重复写入。共同支撑“可恢复”这一目标。

#### 质疑应对
**质疑：你说可恢复，但实际不能自动恢复，这不是虚假宣传吗？**
我不会在简历里写“实现了自动恢复”，我会写“设计了 checkpoint 持久化，为流程恢复提供数据基础”。V1 是可观测性和数据基础，V2 是完整恢复。这个区分我会讲清楚。

---

### Q7：“幂等答案提交”是什么意思？为什么需要？

#### 30 秒简短版
幂等答案提交是指：用同一个幂等键重复提交答案，服务端只处理一次，返回相同结果。防止用户因为网络卡顿点了两次提交，导致答案和评分重复写入。

#### 90 秒深入版
没有幂等会发生什么？用户网卡点了两下提交按钮，可能会生成两个 `UserAnswer`，进而生成两个 `Evaluation`，最终画像被重复更新，导致 `mastery_score` 异常。

我们的做法：幂等键由客户端生成，通过 HTTP Header `Idempotency-Key` 传入。服务端用数据库唯一约束 `(question_id, idempotency_key)` 保证幂等。第二次请求查到已有记录，直接返回已有结果。

#### 追问防御

**Q7.1：幂等键过期吗？**
当前不过期，永久保存。长期保存有两个问题：一是用户用旧 key 提交不同答案会返回第一次结果，可能造成困惑；二是 GDPR 场景下删除历史数据时也需要清理。V2 会考虑 TTL 或显式覆盖机制。

**Q7.2：并发下两个请求同时到达怎么办？**
当前没处理这个场景。两个请求同时查 existing 都为空，会同时写入，第二个触发 `IntegrityError`。正确做法是用 `INSERT ... ON CONFLICT DO NOTHING`，冲突时返回已有记录。

#### 质疑应对
**质疑：这么简单的功能有必要搞幂等吗？**
面试评分直接影响能力画像，一次重复提交会让画像异常。而且“网卡点两下”是非常常见的用户行为。幂等在后端是基本功，花 10 分钟做约束能避免很多麻烦。

---

### Q8：为什么是 3 题？不是 5 题或 10 题？

#### 30 秒简短版
3 题是默认值，可以配置。选择 3 是因为在个人学习场景中，3 题足够覆盖“概念/场景/设计”三类题型，又不至于让一次面试太长，降低用户完成率。

#### 90 秒深入版
默认值 3 有几个考虑：
1. **认知负荷**：一次面试太久，用户会疲劳，评分质量下降；
2. **题型覆盖**：3 题可以循环概念、场景、设计三种题型，让用户接触到不同考查维度；
3. **快速反馈**：短面试能让用户更快看到自己的画像更新，形成正向循环。

但 API 的 `question_count` 字段支持 1 到 10 题，用户可以根据自己的时间调整。

#### 追问防御

**Q8.1：当前支持只练一种题型吗？**
不支持。题型由系统循环选择，用户无法筛选。题目类型存在数据库里，V2 可以在创建 interview 时增加题型过滤参数。

**Q8.2：会追加题目吗？**
当前不会在一次面试中追加。但如果用户答得差，评分会建议 `follow_up_recommended`，并生成复习任务。产品层面可以据此在下一轮面试中多出题。

**Q8.3：题目难度会根据用户表现调整吗？**
V1 不会。当前按固定顺序出题。V2 可以根据画像中的 mastery_score 动态选择题目难度。

#### 质疑应对
**质疑：3 题是不是太少了，测不出水平？**
3 题是默认值，不是上限。而且 AgentMentor 的核心不是“一次面试测出水平”，而是“多次短面试积累画像”。3 题降低了单次成本，提高了完成率，更符合个人学习场景。

---

## 第四部分：可信评分

### Q9：Rubric 四维是哪四维？为什么选这四个？

#### 30 秒简短版
四维是 correctness（正确性）、completeness（完整性）、reasoning（推理过程）、communication（表达清晰度）。选这四个是因为面试不仅考“你会不会”，还考“你能不能讲清楚”。

#### 90 秒深入版
- **correctness**：技术事实是否正确；
- **completeness**：是否覆盖参考答案中的关键要点；
- **reasoning**：解释是否逻辑清晰、有依据；
- **communication**：回答是否条理清楚、易于理解。

communication 对面试场景特别重要。很多后端开发者懂技术，但面试时表达混乱，导致分数被低估。单独评估 communication 能给用户更明确的改进方向。

#### 追问防御

**Q9.1：如果 correctness 高但 communication 低，怎么处理？**
说明用户懂这个知识点但表达不清。总分会被 communication 拉低，feedback 会指出“建议用更结构化的方式组织答案”。这种矛盾不是 bug，而是真实的面试能力分布。

**Q9.2：权重是固定的吗？**
不是。每道题生成时会附带一个 Rubric，每个维度有 weight，总和为 100。权重由 LLM 根据题目类型动态生成，存在 `InterviewQuestionModel.rubric` 字段。

**Q9.3：评分时 LLM 直接输出总分吗？**
不输出。LLM 输出四维分数和各种信号，应用层按固定规则计算总分。这样分数标准可控、可审计、可调整。

#### 质疑应对
**质疑：四个维度够吗？要不要加创新能力、工程经验？**
对 V1 来说四个维度够用了，覆盖了面试中最核心的能力。创新和工程经验可以通过“设计题”和“场景题”间接评估。如果 V2 要做更精细的画像，可以考虑扩展维度，但要避免过度复杂。

---

### Q10：为什么不让 LLM 直接决定最终分数？

#### 30 秒简短版
让 LLM 直接打总分有两个问题：不同 LLM 对“5 分”的理解可能不同，而且黑盒总分无法解释。所以 V1 让 LLM 输出四维信号，应用层按规则计算总分。

#### 90 秒深入版
这其实是“评分即服务”的思路。LLM 提供细粒度信号，应用层做最终决策。

LLM 给出的信号包括：covered_points、missing_points、incorrect_claims、answer_evidence、reference_chunk_ids、feedback、follow_up_recommended、review_reasons、confidence。应用层用这些信号计算总分，并决定是否触发 reviewer 复核。

这样做的好处：
1. **可审计**：能解释为什么用户得 12 分而不是 13 分；
2. **可调整**：想改评分标准不需要重新 prompt LLM；
3. **可降级**：没有 LLM Key 时，可以用规则评分替代。

#### 追问防御

**Q10.1：LLM 评分和规则评分冲突怎么办？**
优先 LLM 评分，因为规则评分（无 Key 降级时）太粗糙，只能做术语重叠和长度判断。但如果 LLM 置信度低（<0.70）或有维度冲突，会触发 reviewer 复核，复核结果优先。

**Q10.2：应用层计算很简单吗？**
当前是四维相加，满分 20。V2 可以根据 Rubric 权重做加权，比如某题 correctness 权重 40%，communication 权重 10%。

#### 质疑应对
**质疑：自己算总分是不是在削弱 LLM 的能力？**
恰恰相反。LLM 擅长理解答案质量，但不擅长给出稳定、可解释的分数。让 LLM 做它擅长的（理解答案），让应用层做它擅长的（稳定规则），是更合理的分工。

---

### Q11：Reviewer 路由是为了解决什么问题？

#### 30 秒简短版
Reviewer 是为了解决 LLM 在边界情况下评分不可靠的问题。对于低置信、维度冲突、接近关键分档的评分，引入第二个 LLM 做复核，避免一次错误评分就进入画像。

#### 90 秒深入版
触发 reviewer 的情况包括：
- confidence < 0.70；
- 维度分数冲突（比如 correctness=5 但 communication=1，差值 ≥4）；
- 接近关键分档且存在争议；
- 引用校验失败或资料证据冲突。

`review_pending` 或 `disputed` 的评分不会更新能力画像，保证画像只基于可信评分。如果 reviewer 一直不可用，interview 不会卡住，但相关评分保持 pending，等恢复后批量处理。

#### 追问防御

**Q11.1：Reviewer 是另一个 LLM 还是人工？**
V1 里是另一个 LLM 调用（用 `review_v1.md` prompt）。设计上可以接入人工 reviewer，但 V1 没有实现人工复核接口。

**Q11.2：两个 LLM 都错了怎么办？**
这是 reviewer 的局限。V2 可以引入三个人工复核机制或更严格的一致性规则。但 V1 的假设是：两个独立 LLM 同时出错的概率比一个 LLM 低。

#### 质疑应对
**质疑：Reviewer 会不会让系统变得很慢？**
会。触发 reviewer 会增加一次 LLM 调用。但 reviewer 只触发在边界 case 上，不是所有评分都走。而且面试场景对实时性要求不像聊天那么高，几秒延迟可接受。

---

## 第五部分：能力画像与学习闭环

### Q12：从 Evaluation 到复习任务的转化是怎么做的？

#### 30 秒简短版
评分完成后，先判断是否需要更新画像（跳过 REVIEW_PENDING 和低置信情况）；然后更新对应 topic 和 subtopic 的 mastery_score；根据最弱维度和错误类型生成 ReviewTask；下次创建面试时优先推荐 open review tasks 对应的知识点。

#### 90 秒深入版
转化流程分四步：
1. **可信性过滤**：只有 confidence >= 0.70 且状态为 FINAL 的评分才更新画像；
2. **画像更新**：更新 `ability_profiles` 中对应 topic 和 subtopic 的 `mastery_score`、`confidence_weighted_count`、`version`；
3. **生成复习任务**：比如 completeness 最低生成 MISSING_DETAIL 类型任务，correctness 最低生成 CONCEPT_CONFUSION 类型任务；
4. **下一轮推荐**：`recommend_interview_plan` 返回最多 5 个推荐知识点，优先级是 open review tasks > 覆盖率缺口 > 低掌握度能力。

#### 追问防御

**Q12.1：复习任务具体长什么样？**
包含 task_type（如 MISSING_DETAIL）、关联的 topic/subtopic、优先级、创建时间、完成条件（如连续两次高分解锁）。

**Q12.2：如果用户一直没完成复习任务，会不会堆积？**
会。V2 需要任务过期和重新排序机制，避免用户被大量 open tasks 压垮。

#### 质疑应对
**质疑：画像更新会不会被一次偶然失误拉偏？**
不会。mastery 更新用类 EMA 公式，learning_rate 最高只有 0.35，单次评分影响有限。而且 ReviewTask 有 verification streak 机制，连续两次高分解锁任务才算真正掌握。

---

### Q13：能力画像里都有什么？

#### 30 秒简短版
画像不是简单总分，而是两层掌握度模型：topic 层（如 RAG、LangGraph）和 subtopic 层（如 RAG 下的检索与召回、证据引用）。每层都有 mastery_score（0-1）和置信度加权计数。

#### 90 秒深入版
画像分两层：
- **topic 层**：如 RAG、LangGraph、Java 后端等；
- **subtopic 层**：如 RAG 下的“检索与召回”、“证据引用”、“生成边界”等。

每层都有 `mastery_score`（0-1），以及 `confidence_weighted_count`、`version` 等元数据。

用户能通过 `/api/v1/profiles` 接口看到自己的画像。V1 前端主要聚焦在面试流程，画像展示做得比较基础。

#### 追问防御

**Q13.1：topic 和 subtopic 是怎么定义的？**
目前维护在 `profile_taxonomy.py` 里，是手动定义的两层分类树。V2 可以考虑让 LLM 自动从资料中提取知识点结构。

**Q13.2：画像实时更新吗？**
是的。每次 trusted evaluation 完成后立即更新对应 topic 和 subtopic。

#### 质疑应对
**质疑：两层画像是不是太复杂了？**
对 V1 来说是必要的，因为面试准备需要精细化到具体知识点。如果只给一个总分，用户不知道从哪里补。两层结构让复习任务更有针对性。

---

## 第六部分：工程取舍与架构

### Q14：V1 为什么不用 Redis、Celery、Kafka、ES、K8s 或本地大模型？

#### 30 秒简短版
这个取舍 list 是为了把复杂度控制在“个人开发机可复现”范围内。每个工具都能解决特定问题，但 V1 的场景用不上：单机低并发不需要 Redis/Celery/Kafka，PostgreSQL 全文检索够用不需要 ES，单机部署不需要 K8s，16GB 机器跑本地大模型体验不好。

#### 90 秒深入版
- **Redis**：缓存、队列、会话。V1 单机低并发，PostgreSQL 够用；
- **Celery**：异步任务队列。ingestion 和评分都是同步或轻量后台处理，不需要独立 worker；
- **Kafka**：事件流。没有多服务协作，不需要；
- **Elasticsearch**：全文检索。PostgreSQL 的 `tsvector` 已经够用；
- **Kubernetes**：容器编排。单机 Docker Compose 就够了；
- **本地大模型服务**：需要 GPU 或大量内存，16GB 机器上体验不好。

我用一个词概括这个思路：**复杂度预算**。V1 的预算必须花在核心闭环上，而不是基础设施。

#### 追问防御

**Q14.1：V2 最先引入哪一个？**
Redis。用于 rate limit、缓存热点检索结果、会话状态。如果要做多实例部署，再引入 Kubernetes。

**Q14.2：PostgreSQL + pgvector 能撑到什么程度？**
个人用户和小团队，几万到几十万条 chunk、并发用户几十人。如果到千级用户或百万级 chunk，需要把向量检索拆到专门数据库。

**Q14.3：什么叫“可复现”？**
任何有 Docker 的机器，执行 `docker compose up` 就能跑通完整系统，不需要手动安装 PostgreSQL、pgvector、Python、Node，也不需要配置 GPU。

#### 质疑应对
**质疑：这种减法会不会让 V1 看起来很简陋？**
恰恰相反。能主动做减法比盲目堆技术更难。V1 的目标是验证学习闭环是否成立，不是展示架构有多复杂。等验证了核心价值，V2 再按需引入基础设施。

---

### Q15：为什么前端用 Vite + React，但运行时却用 Python 提供静态服务？

#### 30 秒简短版
为了简化部署。Vite 负责开发和构建，构建产物由 Python 的 `ThreadingHTTPServer` 在运行时提供。这样运行时只需要一个 Python 容器，避免额外 Node/Nginx 镜像依赖。

#### 90 秒深入版
好处：减少运行时镜像数量，一个 frontend 容器同时做静态服务和 API 代理。

坏处：`ThreadingHTTPServer` 不是为生产环境设计的。每个请求一个线程，几十并发可以应付，但几百并发或长连接会有问题；没有优雅关闭、没有超时配置、没有连接池优化。

生产环境会换成 Nginx 或 Node 静态服务器 + 反向代理。

#### 追问防御

**Q15.1：前端怎么调用后端？**
前端代码在浏览器里直接调用 `/api/v1/*`，这些请求先打到 frontend 容器的 Python proxy，再由 proxy 转发到 api 容器。前端不需要知道后端的实际地址和端口。

**Q15.2：代理有没有安全问题？**
当前 proxy 透传所有 header，只排除 host/content-length/connection。V2 应该改成白名单透传，过滤 X-Forwarded-*、Cookie、Referer 等敏感 header。

#### 质疑应对
**质疑：为什么不直接用 Nginx？**
Nginx 很好，但会增加一个镜像和一份配置。V1 的核心目标是“个人开发机一键跑通”，所以用了 Python 内置 server。这是有意识的 trade-off，不是不知道 Nginx 更好。

---

### Q16：无模型 Key 的情况下怎么降级运行？

#### 30 秒简短版
无 Key 时，系统通过 Development/Fake 适配器降级：Embedding 用 BLAKE2b 哈希生成确定性向量，出题和评分用模板和规则。流程能跑通，但质量会明显下降。

#### 90 秒深入版
- **Embedding 降级**：用 `DevelopmentEmbeddingGateway`，基于 BLAKE2b 哈希生成确定性向量。它保证“相同文本得到相同向量”，但不保证语义相似性。
- **LLM 降级**：出题用模板生成，评分用规则计算（术语重叠、长度、Rubric 覆盖、弱信号词等）。

降级后和真实 LLM 差距很大。RAG 检索几乎退化成字面匹配，评分只能给出粗略分数。

这个降级主要是为了**测试方便和离线演示**，让没有 API Key 的用户也能验证流程。真实学习必须配置 API Key。

#### 追问防御

**Q16.1：无 Key 模式用户上传资料还有意义吗？**
有意义但有限。资料会被解析、分块、入库，检索时只能做字面匹配。它证明了系统能跑通全流程，但学习效果不如配 Key。

**Q16.2：你会不会把这个作为核心卖点？**
我会说“本地可运行、无 Key 可演示”，但不会说“无 Key 效果一样好”。真实价值在有 Key 模式下。

#### 质疑应对
**质疑：无 Key 模式是不是自欺欺人？**
不完全是。它有两个真实价值：一是让开发者和面试官能在没有 API Key 的环境快速验证系统；二是展示了系统的降级设计能力。但我会诚实说明它的局限性。

---

## 第七部分：深入挑战

### Q17：如果从小工具变成真正有人用的产品，最大的三个工程挑战是什么？

#### 30 秒简短版
1. **多用户隔离**：知识库、会话、画像必须按用户隔离；
2. **API 调用成本控制**：LLM token、Embedding、存储都需要计费、限流、配额；
3. **可观测性与可靠性**：真实用户场景下，伪流式、裸异常捕获、无重试策略都会暴露问题。

#### 90 秒深入版
**多用户隔离**：我会先用 row-level security + `user_id` 字段做软隔离，成本低；等对隔离性要求更高时，再考虑按 schema 或按数据库隔离。

**API 成本控制**：按用户设置配额和 rate limit；缓存常见问题的检索结果和答案；对长文档分块后做批量 Embedding；监控每个接口的 token 消耗并告警。

**可观测性与可靠性**：补全日志、metrics、健康检查；把伪流式改成真 SSE；收窄异常捕获范围；加指数退避重试。

#### 追问防御

**Q17.1：敏感或侵权内容怎么处理？**
上传时做内容审核；提供举报和删除机制；在用户协议中明确责任归属；对明显侵权内容做隔离和人工复核。

**Q17.2：多租户数据安全怎么保证？**
文件存储按用户隔离；访问控制确保用户只能访问自己的资料；数据库查询都带 user_id 过滤；对管理员操作加审计日志。

#### 质疑应对
**质疑：你说这么多 V2 要做的事，是不是说明 V1 很不成熟？**
V1 的目标就是验证核心闭环。一个个人项目不可能一开始就做到生产级。我能清晰列出生产化的差距，反而说明我对项目有真实认知。

---

### Q18：项目里有没有用到 LangChain、LangGraph？为什么？

#### 30 秒简短版
V1 没有使用。我自己实现了 LLMGateway、KnowledgeRetriever、EmbeddingGateway、RRF 融合、Rubric 评分、面试状态管理。原因是为了理解底层 trade-off、保持可控、精简依赖。

#### 90 秒深入版
自己实现的抽象包括：
- `LLMGateway`：LLM 调用端口；
- `KnowledgeRetriever`：检索端口；
- `EmbeddingGateway`：Embedding 端口；
- RRF 融合逻辑；
- Rubric 评分和 Reviewer 路由；
- 面试状态管理。

如果 V2 要支持多 Agent 协作（出题 Agent、评分 Agent、复习计划 Agent 之间的状态流转），我会引入 LangGraph。因为复杂状态机、工具调用、checkpoint 持久化自己写成本高。

#### 追问防御

**Q18.1：自己写最大的收获和坑是什么？**
收获是真正理解了 RAG 每个环节的 trade-off：检索、重排、引用校验、prompt 工程、评分，不是调一个库就能解决的。坑是“自己写状态管理很容易把线性流程误称为工作流引擎”——我之前用 `workflow` 命名其实不太准确，它更像带 checkpoint 的状态标签系统。

**Q18.2：如果别人说你重复造轮子，你怎么回应？**
承认 V1 确实重新实现了部分能力，但这不是为了造轮子而造，而是为了理解和控制。Ports 设计已经预留了替换空间，V2 可以平滑接入 LangChain/LangGraph，不会推翻现有设计。

#### 质疑应对
**质疑：为什么不用 LangChain 的 BaseRetriever？**
我们的 `KnowledgeRetriever` 本质上就是 BaseRetriever 的角色。当时没引入 LangChain 是因为不想引入它的依赖树。但接口设计上是兼容的，未来要接 LangChain 只需要写一个适配器。

---

### Q19：能不能用最简单的话解释六边形架构？

#### 30 秒简短版
六边形架构就是“业务核心放中间，外部依赖都通过端口接进来”。换数据库、换 LLM 供应商、换向量检索实现，都不应该影响业务逻辑。

#### 90 秒深入版
我打个比方：domain 层是 CPU，ports 是接口规范，infrastructure 和 API 是外设。你换鼠标、换键盘、换显示器，不需要改 CPU 的指令集。

我的 ports 有：
- `LLMGateway`：LLM 调用；
- `KnowledgeRetriever`：检索；
- `EmbeddingGateway`：Embedding。

domain 层是状态机和值对象，比如 `InterviewStatus`、`EvaluationOutput`，不依赖外部。application 层是用例编排，比如 `InterviewService`、`EvaluationService`，它们组合 domain 和 ports 完成业务用例。

但也要诚实：**数据持久化层目前没有通过 port 隔离**，Application 层直接操作 SQLAlchemy ORM 模型，这是 V1 的架构缺口。

#### 追问防御

**Q19.1：换 LLM 供应商要改多少代码？**
如果兼容 OpenAI API，基本只需要改 `main.py` 的初始化配置；如果不兼容，新增一个适配器实现 `LLMGateway`，业务层代码不动。

**Q19.2：换向量数据库呢？**
新增一个 `KnowledgeRetriever` 适配器，application 层不动。

**Q19.3：数据持久化缺口怎么补？**
V2 按聚合根引入 Repository Pattern，从 `InterviewSession` 开始。接口放 `ports/repositories.py`，实现放 `infrastructure/database/repositories/`。

#### 质疑应对
**质疑：你说六边形架构，但数据持久化没隔离，这不是名不副实吗？**
您说得对，当前只完成了一半。LLM/检索/Embedding 通过 ports 隔离了，但数据库没有。这是 V1 为了快速跑通功能做的妥协。V2 首要任务就是补 Repository，让六边形架构完整。

---

## 第八部分：项目反思与收尾

### Q20：如果让你重新做这个项目，你会在哪个决策上做出不同的选择？

#### 30 秒简短版
我会从一开始引入 Repository Pattern，避免 Application Service 直接操作 ORM 模型。

#### 90 秒深入版
这是架构设计上的决策。当时为了快速跑通功能，直接把 SQLAlchemy 模型塞进了 service 层。付出的代价：
- 单元测试困难，业务逻辑离不开数据库；
- 六边形架构纯度不够，换数据库成本高；
- 事务边界散乱，容易出现状态不一致。

弥补方式：V2 按聚合根逐个引入 Repository，从 `InterviewSession` 开始，同时补 API 契约测试和 PostgreSQL 集成测试。

#### 追问防御

**Q20.1：除了 Repository，还有什么决策想改？**
另一个是想更早引入 eval 集和自动化评估。V1 虽然有 30 条手工标注数据，但没有自动 runner，无法量化每次改动对检索质量的影响。

#### 质疑应对
**质疑：你既然知道，为什么不现在改？**
时间和优先级。V1 的核心目标是跑通闭环，证明这个学习工具有价值。现在闭环已经验证，V2 的重点就是补工程债。我已经把 Repository 和测试覆盖排到了最前面。

---

### Q21：这个项目里你最自豪的一个设计是什么？

#### 30 秒简短版
我最自豪的是“应用层计算总分 + Reviewer 路由”的评分设计。它让评分可审计、可调整，并对边界情况做复核，避免一次错误评分污染能力画像。

#### 90 秒深入版
这个设计花了我大约一周时间，包括 prompt 迭代、规则降级、画像更新逻辑。

验证方式：用 eval 集看评分分布是否合理，检查 LLM 输出是否符合 `EvaluationOutput` schema，对比无 Key 降级评分和 LLM 评分的差异。但 30 条数据太少，没有大规模 A/B 测试。

#### 追问防御

**Q21.1：如果有人说过度工程？**
面试评分直接影响能力画像和复习计划，一次错误评分会让用户长期被误导。把总分计算放在应用层、对边界评分做复核，是为了保证整个学习闭环的可信度。这个复杂度在面试训练场景下是值得的。

**Q21.2：还有没有别的自豪点？**
另一个是无 Key 降级设计。虽然效果不如真实 LLM，但它展示了系统在遇到外部依赖不可用时的韧性，这种“可降级”思维在 AI 系统中很重要。

---

### Q22：如果我用一句话总结你的项目是“一个带引用的 RAG 问答 + 模拟面试 demo”，你会怎么反驳？

#### 30 秒简短版
RAG demo 解决的是“我问、你答”的一次性问题，AgentMentor 解决的是“上传资料 → 出题 → 答题 → 评分 → 画像 → 复习”的持续性学习闭环。

#### 90 秒深入版
工程上也不只是 demo：有完整的无 Key 降级策略、幂等提交、checkpoint 持久化、Reviewer 路由、能力画像和复习任务生成。产品目标是成为个人面试教练，而不是一次性问答工具。

#### 质疑应对
**质疑：但你说很多功能 V1 还不完善，比如 checkpoint 不能自动恢复。**
是的，V1 是 MVP，有明确的边界。但核心闭环已经跑通，而且每个设计都有清晰的演进方向。这不是 demo，是产品雏形。

---

## 源码口述：被追问到实现时的表达方式

这部分不是让你背诵代码，而是准备一套**能在面试中口述出来的实现路径**。面试官问到"你具体怎么做的"时，你可以按这个节奏回答。

---

### SO1：RAG 回答 `AnswerService.answer`

**代码定位**：`src/agent_mentor/application/answer_service.py`，`answer()` 方法。

**输入输出**：输入是 `knowledge_base_id` + `question` + 是否允许模型补充；输出是 `AnswerResult`，包含回答、引用、候选片段、证据是否充分、生成模式、降级原因。

**口述版流程**：

> "`answer` 方法先做混合检索，拿到候选 chunk；然后做一层**词法支持校验**，过滤掉只相似但不相关的片段。如果最高分 chunk 的得分低于阈值，且不允许模型补充，就直接进入 evidence_guard，返回'资料不足'。
> 如果证据够，就调用 `_generate_answer`。这里有两条路：如果配了 LLM，就调用 `generate_structured`，让模型输出 `GroundedAnswerOutput`，包含 answer、citation_chunk_ids 和 evidence_sufficient；如果没配 LLM，就走确定性降级，按引用片段拼接回答。
> 无论哪条路，最后都会调用 `_persist`，把会话、用户消息、助手消息和引用写进数据库，整个 persist 在一个 `async with session` 事务里。"

**关键步骤**：
1. `_retriever.retrieve()` → 混合检索；
2. `_supported_candidates()` → 词法支持过滤；
3. `_generate_answer()` → LLM 或确定性降级；
4. `validate_citations()` → 校验 LLM 引用的 chunk_id 必须在候选里；
5. `_persist()` → 写入 `ChatSessionModel`、`ChatMessageModel`、`ChatCitationModel`。

**失败处理**：
- LLM 失败 → 日志 + 确定性降级；
- 证据不足 → evidence_guard 模式，不编造答案；
- LLM 引用非法 chunk_id → `AppError("LLM_OUTPUT_INVALID")`。

**事务边界**：`_persist` 内所有写入在一个 `AsyncSession` 事务中，`await session.commit()` 提交。

---

### SO2：答题幂等 `InterviewService.submit_answer`

**代码定位**：`src/agent_mentor/application/interview_service.py`，`submit_answer()` 方法。

**输入输出**：输入是 `session_id`、`question_id`、`answer_text`、`idempotency_key`；输出是当前面试状态的 `InterviewSnapshot`。

**口述版流程**：

> "`submit_answer` 首先在同一数据库事务里查面试和题目，校验题目是否属于这个面试、面试是否处于 `WAITING_FOR_ANSWER` 状态、题目是不是当前题。
> 然后用 `idempotency_key` 查 `UserAnswerModel`，如果已经存在，直接返回 snapshot，保证重复提交不会多写。
> 写入答案后，打一个 `persist_answer` 的 checkpoint。接着判断是不是最后一题：如果是，就把状态改成 `COMPLETED`，打 `finish_interview` checkpoint；如果不是，就推进 `current_question_index`，生成下一题，再打 `wait_for_answer` checkpoint。最后 commit。"

**关键步骤**：
1. 加载 `InterviewSessionModel` 和 `InterviewQuestionModel`；
2. 校验 `question.session_id == session_id`；
3. 校验 `interview.status == WAITING_FOR_ANSWER`；
4. 校验 `question.sequence == current_question_index + 1`；
5. 幂等检查：`select UserAnswerModel where question_id + idempotency_key`；
6. 写入 `UserAnswerModel`；
7. 打 checkpoint；
8. 判断是否完成 → 更新状态或生成下一题；
9. `await db.commit()`。

**失败处理**：
- 状态不对 → `AppError("WORKFLOW_STATE_CONFLICT", 409)`；
- 幂等命中 → 直接返回已有结果；
- 生成下一题失败 → 整个事务回滚，不会留下不一致状态。

**事务边界**：所有操作在同一个 `AsyncSession` 中，提交前所有状态变更都是原子的。

---

### SO3：评分流程 `EvaluationService.evaluate_interview`

**代码定位**：`src/agent_mentor/application/evaluation_service.py`，`evaluate_interview()` 和 `_evaluate_answer()`。

**输入输出**：输入是 `interview_id`；输出是每条题目对应的 `EvaluationItem` 元组。

**口述版流程**：

> "评分在面试完成后触发。`evaluate_interview` 先校验面试状态是 `COMPLETED`，然后按顺序遍历每道题，拿到主答案。如果某道题已经有评价，就跳过，避免重复评分。
> 对每道题调用 `_evaluate_answer`：先查这道题允许引用的 chunk_id 白名单，然后尝试用 LLM 生成结构化的 `EvaluationOutput`。如果 LLM 不可用或调用失败，就走确定性降级评分。
> 拿到评分后，应用层会检查是否需要复核。如果置信度低、有争议点或出现自洽问题，并且 reviewer 可用，就再走一遍 `_review_deterministically`。如果复核后总分和原分差 5 分以上，就标记为 `DISPUTED`，不进入画像；否则用复核结果覆盖。
> 最后把 `EvaluationModel` 和 `EvaluationReferenceModel` 写入数据库。"

**关键步骤**：
1. `_get_completed_interview()` → 校验面试完成；
2. `_questions()` → 按 sequence 取所有题目；
3. `_validate_rubric()` → 校验 Rubric 格式；
4. `_primary_answer()` → 取每道题的第一个答案；
5. `_evaluate_with_llm_or_fallback()` → LLM 评分或确定性降级；
6. `_assert_allowed_references()` → 校验引用 chunk_id 在白名单内；
7. `should_review()` / `initial_review_route()` → 判断是否需要复核；
8. `_review_deterministically()` → 复核逻辑；
9. 写入 `EvaluationModel` + `EvaluationReferenceModel`。

**失败处理**：
- 面试未完成 → 409；
- Rubric 格式错误 → 422；
- LLM 失败 → 降级评分；
- 引用非法 → AppError。

**事务边界**：整个 `evaluate_interview` 在一个 `AsyncSession` 中，`await db.commit()` 统一提交。

---

### SO4：面试主流程串联

**代码定位**：`InterviewService.create_interview()`、`start()`、`submit_answer()`。

**口述版流程**：

> "面试主流程分三步。
> **创建**：`create_interview` 只写一条 `InterviewSessionModel`，状态是 `CREATED`，还没有题目。
> **开始**：`start` 校验状态是 `CREATED`，然后改成 `WAITING_FOR_ANSWER`，依次打 `load_profile`、`plan_interview` checkpoint，再调用 `_create_question` 生成第一题，最后打 `wait_for_answer` checkpoint。
> **答题**：`submit_answer` 处理答案、幂等检查、状态推进，到最后一题时改成 `COMPLETED`。
> 所以面试状态机是：CREATED → WAITING_FOR_ANSWER → COMPLETED，错误状态转换会直接抛 409。"

**关键状态转换**：
- `CREATED` → `WAITING_FOR_ANSWER`：start；
- `WAITING_FOR_ANSWER` → `WAITING_FOR_ANSWER`：submit_answer 后生成下一题；
- `WAITING_FOR_ANSWER` → `COMPLETED`：submit_answer 最后一题；
- 其他转换 → `AppError("WORKFLOW_STATE_CONFLICT")`。

**checkpoint 作用**：每个关键节点写 `WorkflowCheckpointModel`，记录当前节点、状态快照、时间戳。前端可以拉 `workflow_trace` 看到完整执行轨迹。

---

### SO5：人物画像更新 `ProfileService.apply_interview_evaluations`

**代码定位**：`src/agent_mentor/application/profile_service.py`，`apply_interview_evaluations()` 和 `_apply_evaluation()`。

**输入输出**：输入是 `interview_id`；输出是 `ProfileSnapshot`，包含能力画像、错误模式、复习任务。

**口述版流程**：

> "画像更新在面试评分之后触发。`apply_interview_evaluations` 加载面试的所有可信评分，对每个 evaluation 调用 `_apply_evaluation`。
> 第一步是 `profile_update_decision`，根据 evaluation 的 status 和 confidence 决定这个评分能不能进入画像。比如 `DISPUTED` 或置信度太低的评分会被拒绝，只记一个 `ProfileUpdateEventModel`，但不去改画像。
> 如果允许更新，就根据面试主题和知识点定位到 topic 和 subtopic 节点，查询或创建对应的 `AbilityProfileModel`，用 `updated_mastery` 渐进更新掌握度。更新时会把置信度作为权重，难题目权重更高。
> 同时，对 subtopic 节点会调用 `classify_error` 识别错误类型，写入 `ErrorPatternModel`，并生成或更新 `ReviewTaskModel`。如果同一错误类型反复出现，任务优先级会上升，复习间隔会缩短。
> 最后，如果用户在相关 subtopic 上拿到了高分，`_advance_review_tasks` 会把对应的复习任务标记为完成。"

**关键步骤**：
1. `_get_interview()` + `_evaluation_rows()` → 加载面试和评分；
2. `profile_update_decision()` → 判断评分是否可信；
3. `canonical_topic()` / `canonical_subtopics()` → 定位画像节点；
4. `_profile_for()` → 查询或创建 `AbilityProfileModel`；
5. `updated_mastery()` → 渐进更新掌握度；
6. `classify_error()` → 识别错误类型；
7. `_record_error_pattern()` → 记录错误模式；
8. `_upsert_review_task()` → 生成复习任务；
9. `_advance_review_tasks()` → 验证通过后关闭任务。

**失败处理**：
- 不可信评分 → 只记录 event，不更新画像；
- 新节点 → 自动创建，初始掌握度 0.5；
- 反复错误 → 提升任务优先级，缩短复习间隔。

**事务边界**：整个 `apply_interview_evaluations` 在一个 `AsyncSession` 中提交。

---

### 源码口述的使用建议

1. **不要背诵代码行号**，记住关键函数名和文件位置即可；
2. **按"输入 → 步骤 → 输出 → 失败处理 → 事务"的节奏讲**；
3. 如果面试官问得更深，比如"`updated_mastery` 具体怎么算"，可以打开 `src/agent_mentor/domain/profile.py` 再讲；
4. 如果面试官问"有没有并发问题"，可以回到幂等键 + 数据库唯一约束 + 事务这三层防线。

---

## 自评

| 维度               | 权重 | 自评（1-5） | 说明                                                 |
| ------------------ | ---- | ----------- | ---------------------------------------------------- |
| 项目定位清晰度     | 15%  | 4.3         | 有架构图和源码定位，项目讲述更立体                   |
| RAG 与可信边界理解 | 20%  | 4.4         | 能口述 `AnswerService` 的 evidence guard 完整链路    |
| 工作流与状态管理   | 15%  | 4.0         | 能讲清 `submit_answer` 的幂等、状态机和 checkpoint   |
| 评分与画像闭环     | 20%  | 4.5         | 能口述评分流程、Reviewer 路由、画像更新              |
| 工程取舍与架构     | 20%  | 4.1         | 源码口述证明对实现细节有掌控，但 Repository 仍未落地 |
| 诚实度             | 10%  | 4.5         | 主动暴露未实现部分，用“边界+计划”包装                |

**加权总分：约 4.2 / 5**

> 最后想说：AgentMentor 是边学边做的 V1，目标是先把闭环跑通。配合源码走读手册和源码口述，常规面试中已能清晰表达项目设计和关键实现。如果继续迭代，优先级是：补 Repository Pattern、补测试覆盖、把 checkpoint 变成真正的恢复机制、把伪流式改成真 SSE。