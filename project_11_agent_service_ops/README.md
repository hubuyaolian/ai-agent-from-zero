# Project 11：Agent 生产化服务与运维

本项目把前序项目里的 Agent 能力收束成一个可上线服务的最小形态：真实 FastAPI 接口、API Key 鉴权、限流、模型网关、fallback、成本统计、trace、metrics、冒烟评估和部署说明。

它不是要把服务做成完整平台，而是让学习者理解：Agent 从 CLI 变成线上服务后，必须补上哪些工程边界。

## 课程定位

前面项目解决的是 Agent 能不能完成任务：

- `project_07_enterprise_rag`：能不能检索、生成、溯源和治理。
- `project_08_workflow_agent`：能不能拆任务、调工具、checkpoint 和重试。
- `project_09_dev_team`：能不能多 Agent 协作交付。
- `project_10_agent_frameworks`：应该如何选框架。

`project_11_agent_service_ops` 解决的是另一个问题：这些 Agent 怎么以服务形式稳定对外提供能力。

## 课程结构

| 文件 | 内容 |
|------|------|
| `PROJECT_PLAN.md` | 项目计划、范围和验收标准 |
| `DAY26.md` | Agent API 服务化、鉴权、限流、SSE 流式输出 |
| `DAY27.md` | 模型网关、成本治理、trace、metrics、eval 和部署 |
| `main.py` | 本地服务启动入口 |
| `api/` | FastAPI app、路由、全局异常处理和请求响应模型 |
| `gateway/` | 模型路由、fallback、预算和成本记录 |
| `security/` | API Key 鉴权和令牌桶限流 |
| `observability/` | trace 事件和 metrics 指标 |
| `evaluation/` | 线上冒烟评估 |
| `deployment/` | Dockerfile 和部署说明 |
| `tests/` | 单元测试和接口契约测试 |

## 运行服务

先安装依赖：

```bash
pip install -r requirements.txt
```

启动服务：

```bash
python project_11_agent_service_ops/main.py
```

默认地址：

```text
http://127.0.0.1:8011
```

默认 API Key：

```text
dev-key
```

## 示例请求

健康检查不需要鉴权：

```bash
curl http://127.0.0.1:8011/health
```

聊天接口需要 `X-API-Key`：

```bash
curl -X POST http://127.0.0.1:8011/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key" \
  -d '{"message": "如何上线一个企业 Agent 服务？"}'
```

SSE 流式响应：

```bash
curl -N -X POST http://127.0.0.1:8011/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key" \
  -d '{"message": "解释 Agent 服务的流式输出。"}'
```

指标接口：

```bash
curl http://127.0.0.1:8011/metrics -H "X-API-Key: dev-key"
```

冒烟评估：

```bash
curl -X POST http://127.0.0.1:8011/eval/smoke -H "X-API-Key: dev-key"
```

## 运行测试

必须在仓库根目录执行：

```bash
python -m unittest discover project_11_agent_service_ops/tests -v
```

如果当前环境没有安装 FastAPI，核心治理测试仍会运行，接口契约测试会自动跳过。

## 学习重点

- Agent 服务不是把 CLI 包一层 HTTP 就结束。
- API Key、限流、预算、fallback、trace、metrics、eval 都应在服务层有明确位置。
- 鉴权失败、限流和预算不足应由统一异常映射转换成 HTTP 状态码。
- 模型网关应在调用模型之前做预算和路由判断，而不是事后补账。
- 本项目的 `/stream` 是 SSE 协议演示；真实 token 流还需要处理中途断开、模型流中断、审计补全和错误传播。
- `BudgetTracker`、`MetricsRegistry`、`TraceRecorder` 是内存教学实现，生产系统应接入数据库、Redis、Prometheus 或 OpenTelemetry。
- 部署不是课程终点，发布后的观测、冒烟评估和回滚能力同样重要。

## 接入前序项目

当前 `ModelGateway.generate()` 返回可预测的演示响应，目的是让治理链路可以离线测试。接入真实 Agent 时，不建议绕过服务治理，而是把真实工作流放在网关之后：

```text
FastAPI -> AgentService -> 鉴权/限流/trace -> 模型网关 -> project_07/08/09 workflow
```

例如企业级 RAG 服务可以在 `AgentService.chat()` 中调用 `project_07_enterprise_rag.graph.workflow`，再把答案、引用来源、token、成本和 trace 写回统一响应。
