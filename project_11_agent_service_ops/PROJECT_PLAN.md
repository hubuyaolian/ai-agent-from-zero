# Agent 生产化服务与运维项目计划书

## 1. 项目概述

本项目是 AI Agent 课程的第 11 个项目，目标是把前面学到的 Agent 能力封装成一个真实可运行的服务形态。

课程重点不是追求复杂平台，而是建立生产化思维：Agent 对外提供服务时，必须有 API 契约、鉴权、限流、模型路由、成本治理、可观测性、冒烟评估和部署边界。

## 2. 教学目标

- 理解 Agent 服务化与 CLI 工具的差异。
- 能用 FastAPI 暴露 `/chat`、`/stream`、`/health`、`/metrics`、`/eval/smoke`。
- 掌握 API Key 鉴权和令牌桶限流的基本实现。
- 掌握全局异常处理，把鉴权、限流和预算错误映射为稳定 HTTP 状态码。
- 掌握模型网关的核心职责：路由、fallback、预算检查、成本记录。
- 掌握 trace、metrics 和 smoke eval 在生产服务中的位置。
- 能解释内存治理模块与生产持久化方案之间的差异。
- 能解释 Dockerfile、`.dockerignore`、健康检查、环境变量和部署配置的最小要求。

## 3. 本期范围

| 模块 | 内容 |
|------|------|
| API 服务 | FastAPI app、请求响应模型、REST 接口、SSE 流式输出 |
| 安全治理 | API Key 鉴权、scope 校验、租户上下文、令牌桶限流 |
| 异常处理 | 全局 exception handler，统一映射 401、429、402 |
| 模型网关 | 模型路由、首选模型、fallback、上下文限制、预算判断 |
| 成本治理 | token 估算、租户费用累计、预算拒绝、生产持久化讨论 |
| 可观测性 | run_id、span、trace event、指标快照、生产导出方案 |
| 质量评估 | 线上冒烟评估，快速发现明显退化 |
| 集成路径 | 说明如何接入 project_07/08/09 的真实 Agent workflow |
| 部署说明 | Dockerfile、`.dockerignore`、非 root 用户、环境变量、健康检查 |

## 4. 非本期范围

- 不接真实云厂商 API Gateway。
- 不实现 OAuth2、JWT、SSO 或企业 IAM。
- 不实现完整 Prometheus / Grafana / OpenTelemetry 后端，只说明导出边界。
- 不实现成本、指标、trace 的数据库持久化，只保留内存教学实现。
- 不连接真实 LangSmith、Phoenix 或 Logfire。
- 不部署到 Kubernetes。
- 不真实调用 LLM，避免测试依赖外部网络和 API Key。

## 5. 两日课程计划

### Day 26：Agent API 服务化

| 序号 | 内容 | 验收 |
|------|------|------|
| 26.1 | FastAPI app 工厂和路由拆分 | 能启动本地服务 |
| 26.2 | 请求响应模型 | 能说明 API 契约为什么要稳定 |
| 26.3 | API Key 鉴权 | 无 Key 或错误 Key 会被拒绝 |
| 26.4 | 令牌桶限流 | 高频请求会返回限流结果 |
| 26.5 | SSE 流式输出 | 能解释本项目是协议演示，不是真 token 流 |
| 26.6 | 全局异常处理 | 能解释为何不在每个路由重复 try/except |

### Day 27：模型网关、观测、评估与部署

| 序号 | 内容 | 验收 |
|------|------|------|
| 27.1 | 模型网关路由 | 能说明 provider、model、priority、fallback |
| 27.2 | 成本预算 | 超预算请求会被拒绝 |
| 27.3 | Trace 与 metrics | 能通过 run_id 追踪一次请求 |
| 27.4 | Smoke eval | 能运行冒烟评估并解释用途 |
| 27.5 | 真实 Agent 集成路径 | 能说明如何接入 project_07/08/09 workflow |
| 27.6 | 部署边界 | 能说清 Dockerfile、`.dockerignore`、健康检查、环境变量和回滚 |

## 6. 交付物

| 文件 | 说明 |
|------|------|
| `DAY26.md` | Agent API 服务化课程 |
| `DAY27.md` | 生产运维治理课程 |
| `main.py` | 本地启动入口 |
| `api/` | FastAPI 接口层 |
| `gateway/` | 模型网关与成本治理 |
| `security/` | 鉴权与限流 |
| `observability/` | trace 与 metrics |
| `evaluation/` | 冒烟评估 |
| `deployment/` | Dockerfile 与部署说明 |
| `.dockerignore` | 容器构建排除规则 |
| `tests/` | 单元测试与接口契约测试 |

## 7. 验收标准

- 服务可以通过 `python project_11_agent_service_ops/main.py` 启动。
- `/health` 可以无鉴权访问。
- `/chat`、`/stream`、`/metrics`、`/eval/smoke` 需要 API Key。
- 鉴权、限流、预算不足由全局异常处理映射成稳定 HTTP 状态码。
- 模型网关能演示 fallback 和预算拒绝。
- trace 和 metrics 能记录请求、模型、token、成本和错误。
- 文档能说明 SSE 演示边界、成本/指标/trace 持久化边界、真实 Agent 集成路径。
- 核心单元测试可以在无外部模型、无网络环境下运行。
- 根目录 README 和 LEARNING_PLAN 更新到 11 个项目 / 27 天。
