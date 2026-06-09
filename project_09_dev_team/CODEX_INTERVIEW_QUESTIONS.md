# Codex 生成的多智能体协同开发团队深度追问面试题

生成说明：本文档由 Codex 基于 `project_09_dev_team` 当前项目结构和实现生成，并参考 `QWAN_INTERVIEW_QUESTIONS.md` 补充源码级追问，用于考察候选人对多 Agent 协同开发、角色分工、消息总线、结构化产物、测试门禁、安全交付和生产化边界的理解。

建议使用方式：让候选人先描述“用户需求如何变成安全交付包”，再按 Planner、Developer、Tester、DocWriter、MessageBus、DeliveryManager 逐层追问。强候选人应能说明为什么开发团队 Agent 必须是受控自动化，而不是全自动写代码落盘。

## 一、多 Agent 架构与项目定位

1. 这个项目为什么要拆成 Planner、Developer、Tester、DocWriter 四类 Agent？
   - 追问：这些角色的职责边界分别是什么？
   - 追问：如果所有事情都交给一个 Agent 做，会带来哪些质量和安全风险？

2. 这个项目和前一个 workflow agent 的核心差异是什么？
   - 追问：project_08 关注工具执行流程，project_09 关注开发产物交付，这两类系统的治理重点有什么不同？
   - 追问：为什么 project_09 更强调沙箱、静态检查、测试和安全落盘？

3. 请完整描述一次 `run "做一个待办事项管理应用"` 的执行链路。
   - 追问：`PlannerAgent -> MessageBus -> DeveloperAgent -> TesterAgent -> 修复循环 -> DocWriterAgent -> DeliveryManager` 每一步输出什么？
   - 追问：哪一步最适合接入人工审批或 diff 预览？

4. 项目计划书为什么强调“所有模型输出都先视为不可信产物”？
   - 追问：LLM 生成代码直接写入仓库根目录有什么风险？
   - 追问：结构化解析、路径白名单、静态检查、测试和质量门禁分别防什么？

5. 多 Agent 开发团队什么时候值得引入，什么时候反而过度设计？
   - 追问：需求复杂度、任务并行性、质量门禁、审计追踪和成本之间如何权衡？
   - 追问：单 Agent + 工具调用能解决的场景，为什么不一定需要多 Agent？

## 二、计划、消息与协作协议

6. `DevelopmentPlan` 为什么要包含 `project_name`、`summary`、`modules`、`tasks`、`interfaces`？
   - 追问：这些字段分别如何指导 Developer、Tester 和 DocWriter？
   - 追问：如果 LLM planner 输出缺少接口定义或验收标准，后续 Agent 会遇到什么问题？

7. `TaskAssignment` 里的 `target_agent`、`module`、`priority`、`dependencies`、`acceptance_criteria` 有什么作用？
   - 追问：当前本地实现没有完全消费所有字段，这是否说明它们没价值？
   - 追问：生产化多 Agent 系统如何利用这些字段做调度、并行和验收？

8. `MessageBus` 为什么要保留 queue 和 history？
   - 追问：queue 解决什么协作问题，history 解决什么审计问题？
   - 追问：如果只用函数返回值，不记录消息历史，会缺少哪些可观测性？

9. `AgentMessage.correlation_id` 的作用是什么？
   - 追问：为什么一次运行内的消息都需要同一个 run_id 关联？
   - 追问：生产系统里还应增加 trace id、span id、user id、tenant id 吗？

10. 消息优先级 `high/normal/low` 在这个项目里如何体现？
    - 追问：测试发现高危问题后，为什么 bug 消息应该高优先级？
    - 追问：真实异步多 Agent 系统中，优先级可能带来哪些饥饿或公平性问题？

11. 当前 MessageBus 是内存实现。生产环境替换成消息队列时，需要补哪些能力？
    - 追问：持久化、确认机制、重试、死信队列、幂等消费、顺序保证分别解决什么问题？
    - 追问：哪些消息可以丢，哪些消息必须可靠投递？

## 三、Planner 与 Developer 产物生成

12. `PlannerAgent` 为什么是规则式规划器？
    - 追问：默认支持 todo、calculator、notes 类需求有什么教学价值？
    - 追问：接入真实 LLM 后，为什么仍然需要 schema validation 和 plan review？

13. `PlannerAgent._project_name()` 用关键词判断项目类型，这种方式的优点和缺点是什么？
    - 追问：如果用户需求同时包含“笔记”和“待办”，系统应该如何处理？
    - 追问：什么时候需要让 planner 输出多模块、多里程碑计划？

14. `DeveloperAgent` 输出的是 `Artifact(path, content, artifact_type)`，而不是直接写文件。为什么？
    - 追问：结构化产物在测试、审计、diff、审批、安全落盘中有什么价值？
    - 追问：如果 Developer 可以直接写磁盘，会破坏哪些安全边界？

15. 当前 Developer 对 `previous_report` 参数没有实际修复逻辑，这暴露了什么教学版边界？
    - 追问：真实修复循环应该如何利用测试反馈？
    - 追问：如何防止修复一个问题时引入新的回归？

16. 生成的 todo 项目里为什么包含模型、存储、命令、CLI 和测试文件？
    - 追问：这体现了怎样的最小项目架构？
    - 追问：如果候选人生成的代码只有一个脚本没有测试，应该如何评价？

17. notes 项目当前通过替换 todo 产物生成，这种做法有什么风险？
    - 追问：简单字符串替换可能造成哪些语义错误？
    - 追问：生产化 Developer Agent 应如何按需求生成真正差异化的模块？

## 四、Tester、质量门禁与修复循环

18. `TesterAgent` 为什么先做路径校验和静态检查，再运行 unittest？
    - 追问：如果产物路径已经越界，为什么不能继续写入临时目录测试？
    - 追问：静态检查能拦截哪些测试运行前的高风险问题？

19. `BANNED_CODE_PATTERNS` 禁止 `eval(`、`exec(`、`os.system(`、`subprocess.Popen(`。这类黑名单有什么价值和局限？
    - 追问：黑名单能不能覆盖所有危险代码？
    - 追问：生产环境还需要哪些沙箱、权限和依赖限制？

20. 为什么测试执行只用白名单 `python -m unittest discover -s tests`？
    - 追问：不执行任意 shell 命令能降低哪些风险？
    - 追问：如果生成项目需要安装依赖或运行数据库，沙箱设计会复杂在哪里？

21. `TestReport.high_or_critical_issues()` 在工作流里起什么作用？
    - 追问：为什么只有 HIGH/CRITICAL 会触发修复循环？
    - 追问：LOW/MEDIUM 问题是否可以带着交付？如何在交付报告里表达？

22. `MAX_FIX_ROUNDS = 3` 的意义是什么？
    - 追问：为什么修复循环必须有上限？
    - 追问：超过上限后应该等待人工确认、降级交付，还是失败退出？

23. 如果 unittest 通过，但代码仍然不满足用户需求，说明当前质量门禁缺了什么？
    - 追问：需求验收、行为测试、端到端测试、人工评审、基准任务集分别如何补上？
    - 追问：测试通过是否等于项目可生产上线？

24. 如果生成代码语法正确、测试通过，但 README 写错了功能说明，当前系统能不能发现？
    - 追问：DocWriter 的输出需要什么校验？
    - 追问：文档和代码一致性如何自动评估？

## 五、安全交付与产物治理

25. `DeliveryManager` 为什么是唯一允许落盘的节点？
    - 追问：这和“所有模型输出不可信”的原则有什么关系？
    - 追问：为什么 Developer、Tester、DocWriter 都不应该直接写目标目录？

26. `validate_artifact_path()` 要禁止绝对路径、空路径、`.` 和 `..`，这些分别防什么？
    - 追问：目录穿越攻击如何让生成产物写出 `data/output/`？
    - 追问：为什么即使校验了相对路径，落盘时还要用 `resolve()` 再判断 parent？

27. `sanitize_project_name()` 在交付目录生成里有什么作用？
    - 追问：如果 project_name 来自 LLM，目录名可能包含哪些危险字符？
    - 追问：项目名冲突时，当前实现会覆盖旧产物吗？生产版应该如何处理？

28. `ARTIFACTS_INDEX.json` 和 `DELIVERY_REPORT.md` 分别解决什么问题？
    - 追问：机器可读产物索引和人类可读交付报告应该包含哪些不同信息？
    - 追问：为什么消息历史也应该进入交付索引？

29. `quality_passed = test_report.passed and not high_or_critical_issues` 是否足够？
    - 追问：如果没有 HIGH/CRITICAL，但有大量 MEDIUM 问题，是否应该通过？
    - 追问：质量门禁应该如何按项目类型、风险等级动态调整？

30. 如果交付目录里已经存在同名文件，系统应该覆盖、版本化、还是失败？
    - 追问：当前教学版行为有什么风险？
    - 追问：生产环境如何支持 diff、回滚和人工确认？

## 六、编排、可观测性与生产化路线

31. 当前 `DevTeamWorkflow` 是顺序编排，但注释说保留可迁移到 LangGraph 的状态边界。哪些字段应该进入 LangGraph state？
    - 追问：`requirement`、`run_id`、`plan`、`code_artifacts`、`test_report`、`fix_count`、`stage` 分别有什么作用？
    - 追问：哪些内容进入 checkpoint 会带来代码泄漏或敏感信息风险？

32. 如果迁移到 LangGraph，哪些节点和条件边最关键？
    - 追问：planning、development、testing、repair_decision、docwriting、delivery 如何建图？
    - 追问：质量门禁失败时，如何通过条件边回到 Developer？

33. 如果接入 OpenAI Agents SDK、AutoGen 或 CrewAI，你会保留哪些本地安全边界？
    - 追问：为什么换框架不能替代路径白名单、静态检查、测试沙箱和人工审批？
    - 追问：框架提供的 handoff、tracing、guardrails 应该如何和现有模块对应？

34. 多 Agent 开发团队的可观测性应该看哪些指标？
    - 追问：计划成功率、测试通过率、修复轮次、交付成功率、高危问题率、人工介入率、平均生成时长分别如何定义？
    - 追问：哪些指标适合进入课程评估集，哪些适合线上监控？

35. 如果用户反馈“生成的项目不能运行”，你会如何排查？
    - 追问：从 history、ARTIFACTS_INDEX、DELIVERY_REPORT、TestReport、临时测试输出、产物路径中按什么顺序定位？
    - 追问：如何判断问题来自 Planner、Developer、Tester、DocWriter 还是 DeliveryManager？

36. 如果把这个项目升级为真实开发助手，你会设计哪些人工确认点？
    - 追问：计划确认、代码 diff、测试结果、权限申请、最终落盘、Git commit/PR 分别是否需要人工确认？
    - 追问：哪些低风险任务可以自动化，哪些必须人工审批？

37. 这个项目的安全测试应该覆盖哪些恶意产物？
    - 追问：绝对路径、`../`、危险代码模式、缺少测试、语法错误、测试失败、伪造通过报告分别如何测试？
    - 追问：为什么安全测试不能只看最终交付目录？

38. 多 Agent 系统如何避免“互相甩锅”或无限修复？
    - 追问：任务验收标准、消息 correlation、修复轮次上限、质量门禁和人工升级机制分别如何发挥作用？
    - 追问：生产环境是否需要 Agent 级别的责任归因和评价指标？

## 七、参考 QWAN 版补充的源码级追问

39. `AgentRole` 使用 `@dataclass(frozen=True)`，并定义了 `responsibilities` 和 `tools`。这种“角色即配置”的设计有什么意义？
    - 追问：当前 `default_roles()` 是否真正参与运行时权限控制？
    - 追问：如果它现在主要用于 `/team` 展示，是否存在“声明了角色边界但没有强制执行”的问题？
    - 追问：你会在 MessageBus、Agent 入口，还是 DeliveryManager 中强制校验角色可用工具？

40. 如果要增加一个 CodeReviewer Agent，你会插入在工作流的哪个位置？
    - 追问：放在 Developer 和 Tester 之间，能补上哪些测试发现不了的问题？
    - 追问：需要修改 `DevTeamWorkflow`、`MessageBus.broadcast()`、`default_roles()`、CLI 展示和交付报告里的哪些内容？
    - 追问：CodeReviewer 的输出应该是 `TestReport`、独立 `ReviewReport`，还是进入 `AgentMessage.attachments`？

41. `PlannerAgent` 和 `DeveloperAgent` 都基于关键词路由。比如需求是“做一个带计算功能的笔记应用”，当前会发生什么？
    - 追问：`_project_name()` 先匹配“计算器”再匹配“笔记”，这种优先级会不会丢需求？
    - 追问：更合理的方案是多标签组合、意图评分，还是让 LLM 输出结构化需求分类？
    - 追问：如果需求同时包含多个子系统，Planner 是否应该拆成多模块计划？

42. `MessageBus.send()` 每次发送后对 `_queue` 全量排序。这个实现的复杂度和潜在瓶颈是什么？
    - 追问：消息量很大时，为什么 `sort()` 会成为热点？
    - 追问：用 `heapq`、优先级队列或分桶队列分别有什么权衡？
    - 追问：如果相同 priority 的消息需要保持 FIFO，当前实现是否可靠？

43. `MessageBus.receive()` 是消费式读取，`history()` 是只读历史。这个设计意图是什么？
    - 追问：queue 和 history 分别服务协作调度和审计追踪中的哪一部分？
    - 追问：如果两个线程同时 `receive("developer")`，当前“先过滤再赋值”的实现是否线程安全？
    - 追问：生产环境应该使用锁、`queue.Queue`、消息队列，还是 Actor runtime？

44. `AgentMessage.correlation_id` 用于关联一次运行的所有消息。当前 MessageBus 是否真正按 `correlation_id` 做隔离？
    - 追问：如果多个 workflow 共用同一个 MessageBus，会不会出现不同 run 的消息混在一起？
    - 追问：`correlation_id` 和 `message_id` 在 distributed tracing 中分别可以对应 trace id 和 span id 吗？
    - 追问：`receive()` 是否应该支持按 receiver + correlation_id 双条件过滤？

45. `MessageBus.broadcast()` 硬编码了 `planner/developer/tester/docwriter` 四个角色。这个设计有什么扩展性问题？
    - 追问：如果动态加入 CodeReviewer 或 SecurityReviewer，硬编码角色列表会造成什么维护成本？
    - 追问：是否应该让 MessageBus 维护 `registered_agents` 注册表？
    - 追问：broadcast 不向发送者自身发送消息，这个行为应该如何测试？

46. `DevTeamState` 定义了 `stage` 字段，但当前 `DevTeamWorkflow.run()` 没有更新它。请设计完整阶段状态机。
    - 追问：阶段是否应包括 `planning -> developing -> testing -> fixing -> documenting -> delivering -> completed/failed`？
    - 追问：每次阶段转移应该记录到 MessageBus、history，还是 checkpoint？
    - 追问：如果迁移到 LangGraph，`stage` 是必要字段还是可以由当前节点推导？

47. 当前修复循环里 `DeveloperAgent.develop(plan, previous_report)` 接收测试报告，但实现没有使用 `previous_report`。这会造成什么问题？
    - 追问：如果 Developer 每次生成相同代码，会不会浪费完整的 `MAX_FIX_ROUNDS`？
    - 追问：如何检测“本轮修复产物和上一轮完全相同”，并提前升级人工处理？
    - 追问：真正的修复逻辑应如何利用 `TestIssue.severity/location/description/suggestion`？

48. `TesterAgent._static_check()` 用字符串匹配 `BANNED_CODE_PATTERNS`。这种方式有哪些绕过手段？
    - 追问：`__builtins__["eval"]`、`getattr(os, "system")`、字符串拼接、base64 解码执行是否能绕过简单黑名单？
    - 追问：用 AST 分析、import 白名单、依赖白名单、RestrictedPython 或容器沙箱分别能补哪些缺口？
    - 追问：黑名单策略为什么不能替代运行时隔离？

49. `TesterAgent._run_unittest()` 在临时目录写入产物后用 `subprocess.run()` 执行 unittest，超时 10 秒。这个测试执行方式有什么安全风险？
    - 追问：如果恶意代码绕过静态检查，测试进程是否仍可能访问本机文件或网络？
    - 追问：为什么“不执行任意 shell 命令”还不等于“安全沙箱”？
    - 追问：生产环境是否需要 Docker、nsjail、seccomp、资源配额和网络隔离？

50. `TesterAgent.review()` 当前只要出现任何 issue，就不会运行 unittest。这个短路策略是否过于保守？
    - 追问：如果只有 LOW 级别问题，是否应该继续执行 unittest？
    - 追问：更合理的策略是否应该只在 CRITICAL/HIGH 时短路？
    - 追问：静态检查和动态测试的结果应该如何合并成最终质量评分？

51. `DevelopmentPlan.tasks` 和 `TaskAssignment.dependencies` 当前没有真正驱动调度。你会如何设计基于任务依赖的多 Agent 调度器？
    - 追问：能否复用 project_08 的拓扑排序思想？
    - 追问：同一层无依赖任务是否可以并行分配给多个 Agent？
    - 追问：TaskAssignment 如何映射到实际 Agent 方法调用和产物验收？

52. `TestReport.high_or_critical_issues()` 只看 HIGH/CRITICAL。如何支持 MEDIUM 问题累积到一定数量也触发修复？
    - 追问：你会用数量阈值，还是 severity 加权分数？
    - 追问：质量门禁是否应该按项目类型动态调整？
    - 追问：交付报告里如何解释“有问题但允许交付”的风险？

53. `Artifact.content` 当前是字符串，`artifact_type` 主要区分 code/doc。如果要支持图片、二进制文件或编译产物，需要怎么改？
    - 追问：是否需要 `content: str | bytes`、`encoding`、`mime_type` 或 `checksum` 字段？
    - 追问：DeliveryManager 什么时候用 `write_text()`，什么时候用 `write_bytes()`？
    - 追问：二进制产物如何做安全扫描和交付索引？

54. `_record_history()` 追加写 `runs.jsonl`，`recent_runs()` 读取全部文件后取最后 N 行。大文件下有什么性能问题？
    - 追问：如何实现从文件末尾反向读取最近 N 行？
    - 追问：是否应该做日志轮转、索引文件、SQLite 存储，还是接入外部日志系统？
    - 追问：history 数据里包含完整 artifacts 和 messages，是否会有体积和敏感信息问题？

55. 如果要加入 human-in-the-loop，在 Developer 生成代码后等待人类 review 再继续测试，你会如何改造？
    - 追问：是否需要新增 `waiting_review` stage、checkpoint、`resume(run_id, approved=True/False)` 接口？
    - 追问：这部分能否复用 project_08 的审批和 checkpoint 模式？
    - 追问：人类拒绝后，Developer 应该收到什么结构化反馈？

56. 对比 project_08 和 project_09，如果要合并成统一 Agent 工作流框架，可以抽象哪些公共层？
    - 追问：规划模型、状态存储、审计日志、路径安全、审批恢复、质量门禁、CLI history 是否能共用？
    - 追问：project_08 的 ToolRegistry 和 project_09 的 MessageBus 分别代表两类执行模型，如何统一接口？
    - 追问：统一框架如何同时支持“工具流程自动化”和“多 Agent 产物交付”？

## 面试评分建议

强候选人通常具备这些特征：

- 能清楚区分多 Agent 协作的价值和成本，知道它适合需要角色隔离、质量门禁和审计追踪的复杂任务。
- 能解释为什么 Developer 只能产出结构化 Artifact，不能直接写磁盘。
- 能从 MessageBus、correlation_id、history、TestReport、DeliveryReport 的角度说明可观测性和责任追踪。
- 能意识到 LLM 生成代码必须经过路径白名单、静态检查、白名单测试、有限修复和人工确认边界。
- 能指出 `AgentRole` 未强制权限、MessageBus 未按 run 隔离、`stage` 未更新、静态黑名单可绕过、unittest 子进程不等于沙箱这些源码级缺口。
- 能把本地顺序编排映射到 LangGraph 条件边、OpenAI Agents SDK tracing/guardrails、AutoGen team runtime 或 CrewAI Flows，但不会把框架能力当成安全替代品。

弱候选人常见表现：

- 把多 Agent 理解成“多个 prompt 分工”，说不清结构化产物、消息协议和质量门禁。
- 认为测试通过就等于交付可信，忽略需求验收、文档一致性和安全审查。
- 让生成代码直接写入仓库或执行任意 shell 命令，缺少沙箱意识。
- 不理解修复循环为什么必须有上限，也说不清何时升级到人工确认。
- 排查失败时只看最终报错，不会追踪计划、消息、测试报告、产物索引和交付报告。
