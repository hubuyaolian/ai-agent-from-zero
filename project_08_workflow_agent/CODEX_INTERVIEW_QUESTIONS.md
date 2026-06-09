# Codex 生成的业务流程自动化 Agent 深度追问面试题

生成说明：本文档由 Codex 基于 `project_08_workflow_agent` 当前项目结构和实现生成，并参考 `QWEN_INTERVIEW_QUESTIONS.md` 补充源码级追问，用于考察候选人对业务流程自动化 Agent、工具注册、计划校验、审批恢复、重试、审计和调度边界的理解。

建议使用方式：让候选人先描述“自然语言指令如何变成可执行工作流”，再按模块追问。强候选人应能把工具元数据、权限审批、依赖拓扑、checkpoint/resume、幂等重试、路径沙箱和生产化编排串成闭环。

## 一、项目定位与整体架构

1. 这个项目和普通聊天 Agent 最大的区别是什么？
   - 追问：为什么业务流程自动化 Agent 更关注计划、工具、副作用、审批和恢复？
   - 追问：如果只用一个 LLM 直接调用工具，会遇到哪些工程风险？

2. 请完整描述一次 `run 读取 data/sales.csv 生成日报` 的执行链路。
   - 追问：`TaskPlanner -> PlanValidator -> WorkflowEngine -> ToolRegistry -> RetryHandler -> AuditLog -> CheckpointStore` 每一层分别承担什么职责？
   - 追问：哪些步骤是“计划阶段”，哪些步骤是“执行阶段”，哪些步骤是“治理边界”？

3. 项目为什么采用“本地顺序执行引擎，但结构映射 LangGraph 节点”的方式？
   - 追问：教学版这样做的收益是什么？
   - 追问：迁移到 LangGraph、Temporal 或 Prefect 时，哪些状态和接口可以复用？

4. 这个项目计划书里强调“教学版可运行 + 生产边界清晰”，你如何解释这个边界？
   - 追问：本地 JSON checkpoint、本地 schedule、JSONL 审计、Python 函数工具分别有什么生产限制？
   - 追问：哪些能力上线前必须替换成生产级组件？

## 二、工具注册与工具治理

5. `ToolRegistry` 为什么不只是一个 `dict[name, function]`？
   - 追问：`ToolMeta` 里的 `group`、`required_args`、`sensitive`、`allowed_roles`、`fallback`、`rate_limit`、`idempotent` 分别有什么意义？
   - 追问：这些元数据如何影响计划校验、审批、重试和审计？

6. `validate_args()` 为什么必须在工具执行前做硬校验？
   - 追问：如果 planner 或 LLM 生成了缺参计划，应该在执行前失败，还是让工具内部报错？
   - 追问：生产环境里为什么更适合用 Pydantic/JSON Schema 做参数校验？

7. `can_execute()` 基于 `allowed_roles` 和 `UserContext.roles` 做权限判断，这个设计的优点和不足是什么？
   - 追问：只做角色交集判断是否足够表达企业权限？
   - 追问：如果工具还需要按部门、租户、数据域、时间窗口授权，应该如何扩展？

8. 为什么 `generate_daily_report`、`write_file`、`send_notification` 这类工具要标记为 `sensitive=True`？
   - 追问：敏感工具和非敏感工具的本质区别是什么？
   - 追问：读文件是否一定不敏感？在什么情况下读取也应该审批？

9. `archive_files` 和 `send_notification` 为什么标记 `idempotent=False`？
   - 追问：非幂等工具如果自动重试，会造成什么后果？
   - 追问：幂等键 `idempotency_key` 在生产系统里应该如何真正落地？

10. 当前工具调用日志只记录 `args_preview` 和 `result_preview`，这有什么价值和风险？
    - 追问：如何避免审计日志记录敏感文件内容或通知正文？
    - 追问：生产级工具网关应记录哪些字段用于追踪和排障？

## 三、任务规划与计划校验

11. `TaskPlanner` 为什么默认使用规则规划，而不是直接让 LLM 生成计划？
    - 追问：规则 planner 在教学项目里的优势是什么？
    - 追问：如果接入 LLM 结构化输出，为什么仍然不能删除 `PlanValidator`？

12. `ExecutionPlan` 和 `Step` 的结构化设计解决了什么问题？
    - 追问：`step.id`、`tool`、`args`、`depends_on`、`requires_approval`、`idempotency_key` 分别对执行有什么影响？
    - 追问：为什么自然语言计划不能直接执行？

13. `PlanValidator` 要拦截哪些计划错误？
    - 追问：未知工具、缺少参数、重复步骤 ID、依赖不存在、自依赖、循环依赖分别会导致什么运行时问题？
    - 追问：哪些属于 fatal error，哪些可以只是 warning？

14. 为什么敏感工具未标记 `requires_approval` 目前是 warning，而不是直接 error？
    - 追问：从安全角度看，这个选择有什么争议？
    - 追问：如果你做生产版，会把它升级成硬拦截吗？

15. 拓扑排序 `execution_order()` 在工作流执行里有什么作用？
    - 追问：如果 planner 输出步骤顺序和依赖关系不一致，应该听谁的？
    - 追问：并行执行时，拓扑图还需要增加哪些约束？

16. `fill_runtime_args()` 支持 `{{step_id}}` 占位符替换，这类机制有什么风险？
    - 追问：依赖步骤输出很长、包含敏感信息、或格式不符合预期时怎么办？
    - 追问：生产环境是否应该对步骤输出建立 schema？

## 四、执行引擎、审批与恢复

17. `WorkflowEngine.execute_plan()` 为什么要先校验计划再执行？
    - 追问：如果计划无效也保存 checkpoint，有什么排障价值？
    - 追问：计划校验和工具执行时校验为什么需要同时存在？

18. 执行引擎如何处理依赖步骤失败？
    - 追问：`_blocked_dependency()` 为什么把后续步骤标记为 `skipped`？
    - 追问：什么情况下应该继续执行不依赖失败步骤的其他分支？

19. 审批逻辑为什么放在 `_execute_step()` 里，而不是只放在 planner 或 CLI 层？
    - 追问：如果用户绕过 CLI 直接调用 engine，会不会仍然被审批拦住？
    - 追问：生产系统里审批状态应该如何持久化和审计？

20. `waiting_approval` 状态下 checkpoint 保存了什么？
    - 追问：为什么 resume 时要跳过已经成功的步骤？
    - 追问：如果 resume 后重新执行已成功的非幂等步骤，会造成什么问题？

21. `CheckpointStore` 用 `run_id` 生成 JSON 文件路径时为什么要清洗 run_id？
    - 追问：如果 run_id 允许 `../` 或绝对路径，会有什么风险？
    - 追问：生产环境的 checkpoint 还需要记录哪些字段，例如 user、tenant、trace、审批人？

22. 当前 `RetryHandler` 只对幂等且 retryable 的操作做指数退避重试，这个策略解决什么问题？
    - 追问：为什么 jitter 能缓解并发重试风暴？
    - 追问：哪些错误应该重试，哪些错误应该立即失败？

23. `WorkflowResult.summary()` 面向 CLI 输出，和审计日志、执行报告有什么区别？
    - 追问：用户可读摘要、机器可读日志、合规审计记录分别应该保留什么信息？
    - 追问：如何避免在摘要里泄漏敏感参数或文件内容？

## 五、路径沙箱、安全与审计

24. `resolve_safe_path()` 为什么把文件读写限制在 `data/` 和 `reports/`？
    - 追问：目录穿越攻击是什么？
    - 追问：为什么相对路径、绝对路径和带项目名前缀的路径都要统一 resolve 后再判断？

25. 如果工具参数是 `../../.env`，系统应该在哪些层拦截？
    - 追问：planner、validator、tool function、policy helper 各自能做什么？
    - 追问：为什么最终路径校验必须靠底层工具或统一 policy，而不能只靠提示词？

26. `AuditLog` 在这个项目里应该支持哪些排障问题？
    - 追问：某一步为什么没执行，是审批、权限、依赖失败、工具异常，还是重试耗尽？
    - 追问：审计记录如何帮助复盘一次误操作？

27. 本地 `TaskScheduler` 只做 daily/weekly 任务注册和查询，这和生产级调度有什么差距？
    - 追问：进程重启、时区、错过执行、并发锁、失败补偿、任务去重分别怎么处理？
    - 追问：什么时候应该引入 APScheduler、Celery Beat、Prefect 或 Temporal？

28. 通知工具当前只是模拟写本地日志。接入真实邮件、飞书、企业微信后，治理要求会发生什么变化？
    - 追问：审批、限流、幂等、收件人白名单、内容脱敏、失败补偿分别如何设计？
    - 追问：通知发送成功但后续步骤失败，工作流应该如何呈现最终状态？

## 六、质量保障与生产化设计

29. 这个项目最关键的自动化测试应该覆盖哪些路径？
    - 追问：路径安全、CSV 统计、敏感审批、resume 跳过已成功步骤、非幂等禁重试、计划循环依赖分别如何测试？
    - 追问：为什么只测试 happy path 不够？

30. 如果用户反馈“日报没生成”，你会如何排查？
    - 追问：从 plan preview、checkpoint、history、errors、工具日志、文件路径、安全策略中按什么顺序定位？
    - 追问：如何判断问题出在规划、权限、审批、工具执行还是报表生成？

31. 如果把规则 planner 替换为 LLM planner，你会加哪些防线？
    - 追问：JSON Schema、工具白名单、计划 diff、dry-run、人工审批、最大步数限制分别防什么？
    - 追问：如何防止 LLM 规划出删除文件、外发数据或无限循环任务？

32. 这个项目迁移到 LangGraph 时，哪些节点应该成为图节点？
    - 追问：planner、validator、approval gate、tool executor、retry handler、reporter、scheduler trigger 如何映射？
    - 追问：哪些状态必须进入 checkpointer，哪些状态不应该持久化？

33. 迁移到 Temporal 这类 durable execution 框架时，和 LangGraph 的关注点有什么不同？
    - 追问：Temporal 更擅长解决哪些问题：长事务、定时器、补偿、activity retry、worker 崩溃恢复？
    - 追问：LangGraph 更适合保留在哪些 Agent 状态和条件路由场景？

34. 如何衡量一个流程自动化 Agent 是否可靠？
    - 追问：计划有效率、审批命中率、工具成功率、重试恢复率、平均执行时长、误操作率、人工介入率分别怎么定义？
    - 追问：哪些指标应进入 CI，哪些应进入线上监控？

35. 如果让你把这个项目升级成企业内部自动化平台，你会给出什么路线图？
    - 追问：工具网关、身份权限、审批流、审计平台、调度器、worker 队列、可观测性、回放和补偿机制分别如何排期？
    - 追问：哪些能力可以 MVP 后补，哪些能力上线前必须完成？

## 七、参考 Qwen 版补充的源码级追问

36. `WorkflowRuntimeState` 目前只是一个 dataclass，注释里说便于后续替换成 LangGraph `StateGraph`。如果真的迁移，需要改哪些地方？
    - 追问：当前 `WorkflowEngine.execute_plan()` 里的线性 `for step in execution_order(plan)`，在 LangGraph 里应该映射成哪些节点、边和条件路由？
    - 追问：`pending_approvals`、`completed_steps`、`failed_steps`、`results` 哪些适合进入 checkpoint，哪些需要脱敏或压缩？

37. `ExecutionPlan` 用 `sha256(instruction + steps)` 生成稳定 `plan_id`，而不是直接用 UUID。这个设计服务什么目标？
    - 追问：内容哈希对计划去重、缓存和审计有什么价值？
    - 追问：同一计划多次执行时，为什么仍然需要单独的 `run_id`？
    - 追问：如果 instruction 只多一个空格就生成不同 `plan_id`，应该如何规范化输入？

38. `PlanValidator._detect_cycle()` 使用 DFS 检测依赖环。请推演 `A -> B, B -> C, C -> A` 会如何被识别。
    - 追问：`visiting` 和 `visited` 分别代表什么？
    - 追问：如果去掉 `visited`，在大型 DAG 中会带来什么复杂度问题？
    - 追问：循环依赖为什么必须在执行前拦截，而不是执行时再发现？

39. `PlanValidator.fill_runtime_args()` 现在只支持简单的 `{{step_id}}` 字符串替换。这个机制有什么局限？
    - 追问：如果上游输出是 JSON，想引用 `{{calc_stats.total_revenue}}`，当前实现能不能支持？
    - 追问：你会选择 JSONPath、jmespath，还是让每个步骤声明输出 schema？
    - 追问：上游输出包含敏感内容时，模板替换是否可能造成下游泄漏？

40. `_execute_step()` 的检查顺序是依赖是否成功、工具是否存在、是否需要审批。这个顺序是否可以调换？
    - 追问：如果先审批再检查依赖，会造成什么用户体验或状态一致性问题？
    - 追问：如果工具不存在但依赖已失败，最终状态应该是 `skipped` 还是 `failed`？
    - 追问：这类顺序选择体现了怎样的状态机优先级？

41. `_overall_status()` 当前按 `failed > approval_required > skipped > success` 归并工作流状态。这个优先级是否合理？
    - 追问：如果同时存在失败步骤和待审批步骤，返回 `failed` 是否会掩盖待审批信息？
    - 追问：真实业务里是否需要区分 `failed_partial`、`waiting_approval_partial`、`completed_with_skips`？
    - 追问：状态枚举设计如何影响 CLI、审计和恢复逻辑？

42. `resume()` 恢复执行时通过 `previous_results` 跳过已成功步骤。如果某一步执行到一半进程崩溃，恢复时会发生什么？
    - 追问：`running` 状态没有成功落 checkpoint 时，恢复后是否会重新执行？
    - 追问：这为什么要求工具具备幂等性或真实的 idempotency key？
    - 追问：生产系统如何记录“步骤已开始但结果未知”的不确定状态？

43. `RetryHandler` 现在支持指数退避和 jitter。如果要扩展断路器模式，需要新增哪些状态？
    - 追问：closed、open、half-open 三种状态分别代表什么？
    - 追问：失败计数、冷却窗口、探测请求和恢复条件应该保存在哪里？
    - 追问：断路器应该按工具维度、用户维度，还是下游服务维度隔离？

44. `UserContext` 使用 `@dataclass(frozen=True)`。为什么执行用户上下文最好不可变？
    - 追问：如果执行过程中 `auto_approve` 被意外改成 `True`，会造成什么安全后果？
    - 追问：resume 时需要变更审批状态，为什么应该创建新的 `UserContext`，而不是修改旧对象？
    - 追问：生产系统里 user、role、tenant、approval scope 是否都应该作为不可变快照进入审计？

45. `AuditLog` 使用按日期分文件的 JSONL，而不是 SQLite。这个选择有什么权衡？
    - 追问：JSONL 追加写、日志收集和流式处理有什么优势？
    - 追问：SQLite 在复杂查询、索引和事务一致性上有什么优势？
    - 追问：`_read_tail()` 为什么从最新文件的末尾读取？如果日志文件很大，当前实现还有什么性能问题？

46. `ToolMeta` 已经定义了 `timeout_seconds`，但 `ToolRegistry.invoke()` 当前没有真正执行超时控制。你会如何补上？
    - 追问：同步函数可以用 `concurrent.futures`、进程隔离或信号机制，各有什么限制？
    - 追问：超时后工具底层副作用可能已经发生，状态和审计应该如何记录？
    - 追问：超时是否应该进入重试逻辑，取决于哪些条件？

47. `ToolMeta.fallback` 和 `ToolRegistry.get_fallback()` 已存在，但主工具失败后不会自动降级。你会如何设计降级执行？
    - 追问：降级是放在 `ToolRegistry.invoke()`、`WorkflowEngine._execute_step()`，还是独立的 fallback policy？
    - 追问：审计日志应该如何记录 `degraded_from`、`degraded_to`、原始错误和降级结果？
    - 追问：哪些工具不应该允许自动降级？

48. `ToolMeta.rate_limit` 字段已定义但未实现。如果要做滑动窗口限流，你会怎么设计？
    - 追问：按工具、用户、角色还是租户维度限流？
    - 追问：滑动窗口可以用 deque 存时间戳，分布式环境下应该换成什么存储？
    - 追问：限流失败应该被视为 retryable error，还是直接进入人工处理？

49. `CheckpointStore.save()` 直接 `write_text()` 写 JSON 文件。机器断电或进程崩溃时会有什么一致性风险？
    - 追问：半写入 JSON 会导致 resume 读取失败，应该如何用临时文件 + `os.replace()` 做原子写？
    - 追问：如果多个进程同时写同一个 `run_id`，需要文件锁还是数据库事务？
    - 追问：checkpoint 数据是否需要版本号，方便未来 schema 迁移？

50. 当前执行引擎是单线程顺序执行。如果两个步骤没有依赖关系，如何支持并行执行？
    - 追问：可以按拓扑层级并行执行，还是让 LangGraph/Temporal 负责调度？
    - 追问：并行执行会给审计顺序、checkpoint 一致性、部分失败处理和审批等待带来哪些复杂度？
    - 追问：并行步骤共享同一输出文件或同一通知渠道时，如何处理资源冲突？

51. 请为这个项目补一套生产级可观测性方案。
    - 追问：当前 `AuditLog`、`ToolRegistry.call_log()`、`WorkflowResult.summary()` 分别覆盖了日志、指标、追踪中的哪一部分？
    - 追问：如果接 OpenTelemetry，你会给 plan、step、tool invocation、retry、approval、checkpoint 分别建哪些 span？
    - 追问：哪些指标应该告警，例如失败率、审批积压、重试耗尽、工具超时、调度延迟？

## 面试评分建议

强候选人通常具备这些特征：

- 能区分交互式 Agent 和流程自动化 Agent，知道后者的关键是可校验计划、受控工具、副作用治理和可恢复执行。
- 能解释 `ToolMeta` 中权限、敏感性、幂等性和参数 schema 对执行安全的影响。
- 能说明为什么 LLM planner 不能越过 `PlanValidator`、审批门禁和工具白名单。
- 能从 checkpoint/resume、非幂等重试、路径沙箱和审计日志角度分析真实企业风险。
- 能深入源码细节，指出 `timeout_seconds`、`fallback`、`rate_limit`、checkpoint 原子性、状态优先级和并行执行这些尚未生产化的缺口。
- 能把教学版本地实现映射到 LangGraph、Temporal、Prefect、Celery、OpenTelemetry 等生产化方向，但不把它们混为一谈。

弱候选人常见表现：

- 只会说“让 Agent 调工具”，解释不清工具元数据和治理边界。
- 把审批当成 UI 功能，而不是执行引擎必须强制执行的安全门禁。
- 忽略非幂等工具重试风险，无法解释为什么通知和归档不能盲目重试。
- 排查失败时只看最终报错，不会看计划、checkpoint、依赖状态、审计和工具日志。
- 不能区分本地教学调度和生产级 durable execution。
