"""主流 Agent 框架选型矩阵示例。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrameworkProfile:
    """一个 Agent 框架的课程选型画像。"""

    name: str
    tier: str
    positioning: str
    strengths: tuple[str, ...]
    best_for: tuple[str, ...]
    not_best_for: tuple[str, ...]
    capabilities: frozenset[str]


@dataclass(frozen=True)
class FrameworkRecommendation:
    """按需求标签计算出的推荐结果。"""

    framework: FrameworkProfile
    score: int
    matched_capabilities: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    rationale: str


_FRAMEWORKS: tuple[FrameworkProfile, ...] = (
    FrameworkProfile(
        name="LangGraph",
        tier="engineering",
        positioning="状态图驱动的长程 Agent 编排框架。",
        strengths=(
            "状态图清晰",
            "支持 checkpoint 和 human-in-the-loop",
            "适合复杂条件分支和可恢复工作流",
        ),
        best_for=("企业流程 Agent", "RAG 工作流", "长程多步骤任务"),
        not_best_for=("只需要一次简单工具调用的聊天机器人",),
        capabilities=frozenset(
            {
                "state_graph",
                "checkpoint",
                "human_in_loop",
                "long_running",
                "workflow",
                "rag_workflow",
                "multi_agent",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="OpenAI Agents SDK",
        tier="engineering",
        positioning="OpenAI 生态原生的 Agent runtime。",
        strengths=(
            "handoff、guardrails、sessions 和 tracing 一体化",
            "MCP 与 sandbox 能力贴近生产 Agent runtime",
            "适合直接使用 OpenAI 模型和工具生态",
        ),
        best_for=("OpenAI 模型体系", "多 Agent handoff", "沙箱工具调用"),
        not_best_for=("强依赖非 OpenAI 生态的统一抽象层",),
        capabilities=frozenset(
            {
                "openai_native",
                "handoff",
                "guardrails",
                "tracing",
                "sandbox",
                "sessions",
                "mcp",
                "multi_agent",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="Google ADK",
        tier="engineering",
        positioning="Google 生态的企业级 Agent 开发、调试和部署套件。",
        strengths=(
            "覆盖开发、运行、评估、部署链路",
            "适合 Gemini 和 Google Cloud 生态",
            "企业集成和运维视角更完整",
        ),
        best_for=("Google Cloud 企业应用", "Gemini 生态", "生产部署"),
        not_best_for=("只想学习最小 Agent loop 的入门项目",),
        capabilities=frozenset(
            {
                "enterprise_deploy",
                "google_cloud",
                "gemini",
                "observability",
                "eval",
                "runtime",
                "multi_agent",
            }
        ),
    ),
    FrameworkProfile(
        name="PydanticAI",
        tier="engineering",
        positioning="强调 Python 类型安全和结构化输出的 Agent 框架。",
        strengths=(
            "Pydantic schema 约束强",
            "依赖注入和 eval 适合业务工程",
            "适合把 LLM 输出变成可校验对象",
        ),
        best_for=("结构化业务输出", "类型安全工作流", "可测试 Agent"),
        not_best_for=("重度多 Agent 社会模拟",),
        capabilities=frozenset(
            {
                "typed_output",
                "dependency_injection",
                "eval",
                "python",
                "hooks",
                "business_rules",
                "structured_output",
            }
        ),
    ),
    FrameworkProfile(
        name="AutoGen",
        tier="engineering",
        positioning="面向多 Agent 对话、事件驱动和代码执行实验的框架。",
        strengths=(
            "多 Agent 对话模型成熟",
            "研究和代码执行实验资料多",
            "Core 层适合事件驱动和分布式扩展",
        ),
        best_for=("研究型多 Agent", "代码执行实验", "协作 Agent 原型"),
        not_best_for=("只需要严格 DAG 编排的业务流程",),
        capabilities=frozenset(
            {
                "research_multi_agent",
                "conversable_agent",
                "code_execution",
                "event_driven",
                "distributed",
                "multi_agent",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="CrewAI",
        tier="engineering",
        positioning="以角色团队和流程控制组织 Agent 协作。",
        strengths=(
            "角色、任务、团队概念容易讲清楚",
            "Crews 和 Flows 适合业务自动化叙事",
            "适合快速搭建研究/内容/运营团队 Agent",
        ),
        best_for=("角色分工型 Agent", "内容生产", "业务自动化团队"),
        not_best_for=("需要底层状态图精细控制的复杂系统",),
        capabilities=frozenset(
            {
                "role_team",
                "flows",
                "business_automation",
                "multi_agent",
                "delegation",
                "content_workflow",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="LlamaIndex Agents",
        tier="engineering",
        positioning="数据和 RAG 强相关的 Agent 能力层。",
        strengths=(
            "数据连接和索引生态强",
            "Query Engine、Retriever 和 Agent 衔接自然",
            "适合知识库和数据密集型 Agent",
        ),
        best_for=("RAG 应用", "文档问答", "数据密集型 Agent"),
        not_best_for=("与数据检索无关的纯流程自动化",),
        capabilities=frozenset(
            {
                "rag_heavy",
                "data_connectors",
                "retrieval",
                "indexing",
                "query_engine",
                "document_qa",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="Semantic Kernel",
        tier="engineering",
        positioning="企业中间件式 AI 编排 SDK。",
        strengths=(
            "插件和函数抽象适合接企业 API",
            "C# / Python / Java 生态覆盖企业开发栈",
            "适合 Microsoft 和 .NET 企业环境",
        ),
        best_for=("Microsoft 企业生态", ".NET 应用", "API 插件编排"),
        not_best_for=("强调研究型多 Agent 对话模拟的任务",),
        capabilities=frozenset(
            {
                "enterprise_dotnet",
                "plugin",
                "api_orchestration",
                "microsoft",
                "csharp",
                "java",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="AgentScope",
        tier="research",
        positioning="面向大规模多 Agent 应用和消息传递的研究/平台型框架。",
        strengths=("消息传递模型明确", "适合多 Agent 仿真和分布式实验"),
        best_for=("大规模多 Agent 仿真", "研究型消息传递实验"),
        not_best_for=("工业业务流程的第一选择",),
        capabilities=frozenset(
            {
                "message_passing",
                "large_scale_agents",
                "simulation",
                "distributed",
                "research_multi_agent",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="CAMEL",
        tier="research",
        positioning="以 role-playing 和 agent society 著称的多 Agent 框架。",
        strengths=("角色扮演协作范式清晰", "适合探索型任务和社会模拟"),
        best_for=("角色扮演实验", "合成数据", "多 Agent 社会模拟"),
        not_best_for=("强治理、强审计的生产流程 Agent",),
        capabilities=frozenset(
            {
                "role_playing",
                "agent_society",
                "simulation",
                "synthetic_data",
                "research_multi_agent",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="Haystack",
        tier="specialized",
        positioning="偏生产 RAG 和 pipeline 的框架。",
        strengths=("RAG pipeline 结构清晰", "适合搜索、问答和 context engineering"),
        best_for=("生产 RAG pipeline", "搜索问答", "文档检索"),
        not_best_for=("多 Agent 角色团队叙事",),
        capabilities=frozenset(
            {
                "rag_heavy",
                "pipeline",
                "retrieval",
                "document_qa",
                "production_rag",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="Agno",
        tier="emerging",
        positioning="新一代 Agent platform 方向框架。",
        strengths=("AgentOS 叙事完整", "强调会话、审计、RBAC 和运行平台"),
        best_for=("Agent 平台原型", "需要会话和审计的应用"),
        not_best_for=("只想稳定教学核心概念的基础课",),
        capabilities=frozenset(
            {
                "agent_platform",
                "sessions",
                "audit",
                "rbac",
                "multi_agent",
                "python",
            }
        ),
    ),
    FrameworkProfile(
        name="Mastra",
        tier="emerging",
        positioning="TypeScript 生态的 Agent 框架代表。",
        strengths=("适合 Node/TypeScript 产品工程", "贴近前后端一体应用"),
        best_for=("TypeScript Agent", "产品型 Web 应用", "Node 生态"),
        not_best_for=("Python 数据和 RAG 主线课程",),
        capabilities=frozenset(
            {
                "typescript",
                "node",
                "product_agent",
                "workflow",
                "web_app",
            }
        ),
    ),
    FrameworkProfile(
        name="Strands Agents",
        tier="emerging",
        positioning="AWS 生态值得观察的 Agent SDK。",
        strengths=("贴近 AWS 工具和云生态", "轻量模型驱动 Agent 叙事"),
        best_for=("AWS 生态探索", "云上 Agent 原型"),
        not_best_for=("当前课程主线的核心必讲框架",),
        capabilities=frozenset(
            {
                "aws",
                "cloud_agent",
                "tool_use",
                "emerging",
                "python",
            }
        ),
    ),
)

_CAPABILITY_DEFINITIONS: dict[str, str] = {
    "agent_platform": "提供 Agent 应用运行平台、会话、权限或管理能力。",
    "agent_society": "以多个 Agent 组成社会或群体进行模拟和协作。",
    "api_orchestration": "编排企业 API、函数或插件调用。",
    "audit": "支持或强调运行记录、审计日志和操作追踪。",
    "aws": "贴近 AWS 云生态和工具链。",
    "business_automation": "面向业务流程自动化和重复运营任务。",
    "business_rules": "适合把业务规则和模型输出校验结合起来。",
    "checkpoint": "能保存中间状态，支持暂停、恢复或回放。",
    "cloud_agent": "适合云上 Agent 原型或云服务集成。",
    "code_execution": "支持或适合代码执行、测试和代码类工具调用。",
    "content_workflow": "适合内容生产、编辑、审稿等流程。",
    "conversable_agent": "以可对话 Agent 作为核心抽象。",
    "csharp": "适合 C# / .NET 技术栈。",
    "data_connectors": "提供较强的数据源连接和加载能力。",
    "delegation": "支持任务委派、角色分工或 Agent 协作分派。",
    "dependency_injection": "支持依赖注入，便于测试和业务对象管理。",
    "distributed": "适合分布式、多进程或大规模 Agent 实验。",
    "document_qa": "适合文档问答和知识库应用。",
    "emerging": "新兴方向，适合观察但不一定作为课程主线。",
    "enterprise_deploy": "关注企业部署、运行时、权限或运维。",
    "enterprise_dotnet": "适合 Microsoft / .NET 企业软件环境。",
    "eval": "支持或强调评估集、质量度量和持续评估。",
    "event_driven": "以事件驱动方式组织 Agent 或消息流。",
    "flows": "支持流程、工作流或结构化任务编排。",
    "gemini": "适合 Gemini 模型生态。",
    "google_cloud": "适合 Google Cloud 生态。",
    "guardrails": "提供安全护栏、输入输出限制或运行时策略。",
    "handoff": "支持 Agent 之间的任务移交。",
    "hooks": "支持生命周期钩子或 middleware 扩展点。",
    "human_in_loop": "支持人工审批、人工中断或人工反馈。",
    "indexing": "支持索引构建、维护或检索优化。",
    "java": "适合 Java 技术栈。",
    "large_scale_agents": "面向大量 Agent 或大规模仿真。",
    "long_running": "适合长时间、多步骤、可恢复任务。",
    "mcp": "支持或适合接入 Model Context Protocol。",
    "message_passing": "以消息传递作为 Agent 协作核心机制。",
    "microsoft": "适合 Microsoft / Azure 生态。",
    "multi_agent": "支持多个 Agent 协作。",
    "node": "适合 Node.js 生态。",
    "observability": "强调 trace、日志、指标或可观测性。",
    "openai_native": "贴近 OpenAI 模型和工具运行时。",
    "pipeline": "适合把多个处理步骤串成可观测流水线。",
    "plugin": "支持插件、函数或工具封装。",
    "product_agent": "适合产品型 Agent 和面向用户的应用。",
    "production_rag": "适合生产级 RAG pipeline 和检索系统。",
    "python": "适合 Python 技术栈。",
    "query_engine": "提供 query engine 或类似数据问答抽象。",
    "rag_heavy": "RAG、检索、索引或数据问答是系统核心。",
    "rag_workflow": "RAG 需要工作流、重试、质量检查或引用治理。",
    "rbac": "强调角色权限或访问控制。",
    "research_multi_agent": "适合多 Agent 研究、仿真或原型实验。",
    "retrieval": "提供检索、召回或搜索能力。",
    "role_playing": "以角色扮演方式组织 Agent 协作。",
    "role_team": "以角色团队和任务分工组织 Agent。",
    "runtime": "提供运行时、任务执行或部署相关能力。",
    "sandbox": "支持或适合沙箱执行、隔离工具调用。",
    "sessions": "支持会话状态或 session 管理。",
    "simulation": "适合模拟、仿真或探索性任务。",
    "state_graph": "用显式状态、节点和边编排 Agent 工作流。",
    "structured_output": "强调结构化输出和程序可解析结果。",
    "synthetic_data": "适合生成合成数据或模拟数据。",
    "tool_use": "支持工具调用或工具接入。",
    "tracing": "支持调用链追踪和运行过程记录。",
    "typed_output": "用类型或 schema 约束模型输出。",
    "typescript": "适合 TypeScript 技术栈。",
    "web_app": "适合 Web 产品或前后端一体应用。",
    "workflow": "支持流程、状态或任务编排。",
}


def list_frameworks() -> tuple[FrameworkProfile, ...]:
    """返回课程覆盖的框架画像。"""
    return _FRAMEWORKS


def list_capability_definitions() -> dict[str, str]:
    """返回 capability tags 的定义表。"""
    return dict(_CAPABILITY_DEFINITIONS)


def get_framework(name: str) -> FrameworkProfile:
    """按名称查找框架。"""
    for framework in _FRAMEWORKS:
        if framework.name.lower() == name.lower():
            return framework
    raise KeyError(f"未知 Agent 框架: {name}")


def recommend_frameworks(
    required_capabilities: set[str],
    *,
    limit: int = 3,
    tier_weight: int = 3,
) -> list[FrameworkRecommendation]:
    """根据需求能力标签推荐框架。

    tier_weight 是课程默认偏置：本项目面向工程落地，所以 engineering
    框架默认加 3 分。需要中性比较研究框架时，可传入 tier_weight=0。
    """
    if not required_capabilities or limit <= 0:
        return []

    recommendations: list[tuple[int, FrameworkRecommendation]] = []
    for index, framework in enumerate(_FRAMEWORKS):
        matched = tuple(sorted(required_capabilities & framework.capabilities))
        missing = tuple(sorted(required_capabilities - framework.capabilities))
        if not matched:
            continue
        score = len(matched) * 10 - len(missing) * 2
        if framework.tier == "engineering":
            score += tier_weight
        recommendations.append(
            (
                index,
                FrameworkRecommendation(
                    framework=framework,
                    score=score,
                    matched_capabilities=matched,
                    missing_capabilities=missing,
                    rationale=_build_rationale(framework, matched, missing),
                ),
            )
        )

    ranked = sorted(
        recommendations,
        key=lambda item: (-item[1].score, -len(item[1].matched_capabilities), item[0]),
    )
    return [item[1] for item in ranked[:limit]]


def _build_rationale(
    framework: FrameworkProfile,
    matched: tuple[str, ...],
    missing: tuple[str, ...],
) -> str:
    matched_text = "、".join(matched) if matched else "无直接匹配"
    missing_text = "、".join(missing) if missing else "无明显缺口"
    return (
        f"{framework.name} 匹配能力：{matched_text}；"
        f"缺口：{missing_text}；定位：{framework.positioning}"
    )
