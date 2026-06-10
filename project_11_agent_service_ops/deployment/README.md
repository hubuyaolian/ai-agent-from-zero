# Project 11 部署说明

## 本地 Docker 运行

在仓库根目录构建镜像：

```bash
docker build -f project_11_agent_service_ops/deployment/Dockerfile -t agent-service-ops .
```

运行：

```bash
docker run --rm -p 8011:8011 \
  -e PROJECT_11_API_KEYS=dev-key \
  -e PROJECT_11_DAILY_BUDGET_CENTS=20 \
  agent-service-ops
```

健康检查：

```bash
curl http://127.0.0.1:8011/health
```

## 生产部署 checklist

- 使用密钥管理系统注入 `PROJECT_11_API_KEYS`。
- 按租户配置预算和限流，而不是所有租户共用默认值。
- `/metrics`、`/eval/smoke` 必须鉴权。
- 容器健康检查使用 `/health`。
- 发布后先跑 smoke eval，再放量。
- 发生模型质量退化时，优先回滚模型路由或 Prompt 配置。
- trace 和 metrics 应接入集中观测平台。

## 教学 Dockerfile 与生产 Dockerfile 的差异

当前 Dockerfile 是教学版，目标是让学习者理解服务容器化的最小结构。生产镜像还应继续强化：

- 使用 `.dockerignore` 排除 `.env`、`.git`、`__pycache__`、`runtime_data/`。
- 使用非 root 用户运行应用。
- 固定依赖版本，并通过内部镜像源或 lock file 构建。
- 采用 multi-stage build 减少镜像体积。
- 增加健康检查，例如定期请求 `/health`。
- 把 API Key、模型 Key、预算和限流配置全部通过环境变量或配置中心注入。
- 不把运行时日志和 trace 长期写在容器本地文件系统。
