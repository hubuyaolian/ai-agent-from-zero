# Day 26：Agent API 服务化、鉴权与流式输出

## 1. 为什么要把 Agent 做成服务

前面的项目大多是 CLI 或本地脚本。CLI 适合教学和验证 Agent 能力，但企业系统通常需要通过 HTTP API 对接业务系统、前端页面、消息平台或内部工作流。

把 Agent 做成服务后，问题会从“模型能不能回答”升级为：

- 谁可以调用？
- 调用频率如何限制？
- 请求和响应格式是否稳定？
- 流式输出如何返回？
- 调用失败如何映射成 HTTP 错误？
- 每次请求能否被审计和追踪？

这就是 `project_11_agent_service_ops` 的重点。

## 2. 服务入口

本项目使用 FastAPI：

```python
from fastapi import FastAPI

app = FastAPI(title="Project 11 Agent Service Ops")
```

入口在：

```text
project_11_agent_service_ops/api/app.py
project_11_agent_service_ops/main.py
```

启动命令：

```bash
python project_11_agent_service_ops/main.py
```

## 3. API 契约

请求模型在 `api/schemas.py`：

```python
class ChatRequest(BaseModel):
    message: str
    preferred_model: str | None = None
```

响应模型不仅返回答案，还返回生产服务关心的信息：

```python
class ChatResponse(BaseModel):
    run_id: str
    answer: str
    model_name: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_cents: float
    fallback_used: bool
    route_reason: str
```

这比单纯返回 `answer` 更接近生产系统。调用方可以知道用了哪个模型、是否降级、成本是多少、后续排查用哪个 `run_id`。

## 4. API Key 鉴权

课程实现位于：

```text
security/auth.py
```

核心流程：

```text
读取 X-API-Key -> 查 key_map -> 生成 AuthContext -> 校验 scope
```

示例：

```python
context = authenticator.authenticate(api_key)
authenticator.require_scope(context, "chat")
```

真实生产系统不要明文存 API Key，应使用 hash 存储或接入密钥管理系统。本课程保留明文是为了本地开箱运行。

## 5. 令牌桶限流

限流实现位于：

```text
security/rate_limiter.py
```

令牌桶逻辑：

```text
桶有固定容量 -> 每秒补充令牌 -> 每次请求消耗令牌 -> 不足时拒绝
```

它解决的是服务保护问题：避免某个租户、用户或异常脚本把模型调用打爆。

## 6. 普通响应与流式响应

普通响应：

```text
POST /chat
```

服务等 Agent 完整处理完，再一次性返回 JSON。

流式响应：

```text
POST /stream
```

服务返回 `text/event-stream`，用 SSE 格式分片输出：

```text
data: 第一段内容

data: 第二段内容

event: done
data: run_xxx
```

真实系统里，流式输出还要考虑客户端断开、模型流中断、审计日志补全和错误传播。

### 本项目的 `/stream` 是协议演示

当前代码先调用 `service.chat()` 得到完整回答，再按句子拆成 SSE 片段。这能教学 SSE 协议格式，但还不是真正的 token-by-token 模型流。

真实流式生成通常长这样：

```python
async def events():
    run_id = trace.new_run_id()
    try:
        async for token in model_gateway.stream(prompt, run_id=run_id):
            if await request.is_disconnected():
                trace.record(run_id, "client.disconnected")
                break
            yield f"data: {token}\n\n"
        yield f"event: done\ndata: {run_id}\n\n"
    except Exception as exc:
        trace.record(run_id, "stream.failed", {"error": str(exc)})
        yield f"event: error\ndata: {str(exc)}\n\n"
```

真实流式服务要额外处理：

- 客户端中途断开时，是否停止模型调用。
- 模型流中断后，审计日志如何补全。
- 已经开始输出 SSE 后，错误不能再简单改 HTTP 状态码。
- token 级输出如何统计成本。
- 长连接如何被网关、负载均衡和超时配置影响。

## 7. Day 26 小结

Agent 服务化的第一步不是换一个框架，而是明确服务边界：

- API 契约要稳定。
- 鉴权要在模型调用前发生。
- 限流要在模型调用前发生。
- 错误要映射成明确 HTTP 状态码。
- 流式输出是协议设计，不只是 `print` 慢一点。
