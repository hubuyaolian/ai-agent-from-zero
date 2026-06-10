# Day 27：模型网关、成本治理、可观测性、评估与部署

## 1. 为什么需要模型网关

当 Agent 进入生产系统后，模型调用不应该散落在业务代码里。更合理的方式是集中走模型网关：

```text
业务请求 -> 模型网关 -> 模型 provider -> 返回结果
```

模型网关负责：

- 选择 provider 和 model。
- 根据上下文长度判断模型是否可用。
- 首选模型不可用时 fallback。
- 调用前估算成本并检查预算。
- 调用后记录 token、费用和模型信息。

本项目实现位于：

```text
gateway/model_gateway.py
gateway/cost_tracker.py
```

## 2. 路由与 fallback

模型路由表包含：

```python
ModelRoute(
    name="deepseek-chat",
    provider="deepseek",
    priority=10,
    max_context_tokens=64000,
    input_cost_per_1k_cents=0.014,
    output_cost_per_1k_cents=0.028,
)
```

当调用方指定 `preferred_model`，网关会先尝试首选模型。如果首选模型不可用，就降级到优先级最高的可用模型。

这对应真实生产里的降级策略：不要让某个 provider 的短暂故障拖垮整个 Agent 服务。

## 3. 成本预算

本项目用字符长度估算 token：

```python
estimate_tokens(text)
```

然后计算费用：

```text
input_tokens / 1000 * input_price + output_tokens / 1000 * output_price
```

调用模型前先检查预算：

```text
已花费 + 本次预估费用 <= 租户预算
```

如果预算不足，直接拒绝请求，而不是先调用模型再补账。

### 本项目成本数据是内存演示

`BudgetTracker` 使用内存列表保存 `UsageRecord`。这适合教学和测试，但不能直接当生产账本：

- 服务重启后费用记录会清零。
- `DAILY_BUDGET_CENTS` 只是预算上限，没有实现跨天重置。
- 多实例部署时，每个进程都有自己的内存账本，会导致预算不一致。
- 生产系统应把成本数据写入数据库、Redis，或接入云厂商账单 API。
- 日预算需要明确时区、日期边界和补偿任务。

## 4. Trace

Trace 解决的是“这次请求到底经历了什么”。

本项目记录：

- `auth.accepted`
- `rate_limit.checked`
- `model_gateway.completed`
- `request.failed`

每次请求都有 `run_id`。真实系统里，`run_id` 应该贯穿 API 网关、Agent 工作流、工具调用、模型调用和日志系统。

## 5. Metrics

Metrics 解决的是“服务整体表现如何”。

本项目统计：

- 请求数
- 错误数
- 输入 token
- 输出 token
- 总成本
- 平均延迟
- 各模型调用次数

接口：

```text
GET /metrics
```

真实系统可把这些指标导出到 Prometheus、OpenTelemetry Collector 或云厂商监控。

本项目的 `MetricsRegistry` 也是内存累计器。生产系统通常不会长期把指标留在应用进程内，而是导出为 Prometheus exposition format，或通过 OpenTelemetry SDK 发送到 Collector。

原因很简单：

- 应用重启会丢失内存指标。
- 多实例服务需要聚合指标。
- 指标需要 TTL、标签、采样和查询能力。
- 看板、告警和 SLO 计算通常不在业务进程内完成。

## 6. Smoke Eval

冒烟评估不是完整质量评测。它适合上线前后快速确认服务没有明显退化。

接口：

```text
POST /eval/smoke
```

典型使用时机：

- 发布前。
- 切换模型后。
- 修改 Prompt 后。
- 修改检索链路后。
- provider 故障恢复后。

完整生产系统还需要离线评估集、人工标注、回归分数和失败样本分析。

## 7. 如何接入前序项目的真实 Agent

本项目为了测试稳定，没有真实调用 LLM。要接入前序项目，可以把 `AgentService.chat()` 里的：

```python
gateway_response = self.gateway.generate(...)
```

替换为真实工作流调用。典型集成路径：

```text
project_11 API 层
-> AgentService.chat()
-> 鉴权 / 限流 / trace
-> 调用 project_07_enterprise_rag 的 LangGraph workflow
-> 把 answer、sources、token、cost 写回 ServiceResponse
-> metrics / audit / eval
```

接入 `project_07_enterprise_rag` 时，建议保留模型网关位置：RAG workflow 内部真正调用模型前仍应经过统一网关。这样成本、fallback 和 trace 不会散落到各项目里。

## 8. Trace 持久化边界

`TraceRecorder` 当前把事件留在内存里，只适合单进程教学。生产系统应该把 trace 导出到 OpenTelemetry Collector、Jaeger、Zipkin、LangSmith、Phoenix 或云厂商链路追踪。

需要额外设计：

- trace 数据保留周期。
- PII 和敏感参数脱敏。
- 失败请求的采样策略。
- run_id 如何贯穿 API 网关、Agent workflow、工具调用和模型 provider。
- trace 查询权限，避免把用户输入暴露给不相关人员。

## 9. 部署边界

本项目提供 `deployment/Dockerfile`，但课程重点是理解部署必须补哪些配置：

- API Key 不能写进镜像。
- 预算、限流、模型路由应通过环境变量或配置中心管理。
- `/health` 用于健康检查。
- `/metrics` 应受保护，不能公开暴露。
- 发布后要跑 smoke eval。
- 出现质量退化时要能回滚模型、Prompt 或服务版本。

## 10. Day 27 小结

Agent 生产化不是单点能力，而是一组治理闭环：

```text
路由 -> 预算 -> 调用 -> trace -> metrics -> eval -> 发布/回滚
```

框架能帮助编排 Agent，但不能自动替代这些服务治理能力。
