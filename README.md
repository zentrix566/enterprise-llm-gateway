# Enterprise LLM Gateway

企业级大模型统一接入与能力评估平台。当前版本通过 OpenAI 风格的统一接口接入 DeepSeek 与阿里云百炼千问，并提供 Mock 模型、流式输出和请求关联标识，为后续限流、预算控制及评测系统建立基础。

## 主要功能

- 提供 `/v1/models` 模型发现接口
- 提供 `/v1/chat/completions` 统一聊天补全接口
- 支持普通响应和 SSE 流式响应
- 内置无需 API Key 的 `mock-echo` 模型
- 支持 `deepseek-v4-flash` 和 `deepseek-v4-pro`
- 支持 `qwen3.6-flash` 和 `qwen3.7-plus`
- 复用 OpenAI 兼容适配器，隔离不同模型供应商的配置
- 为每次请求生成或透传 `X-Request-ID`
- 记录每次调用的供应商、模型、状态、延迟和 Token 用量
- 提供 `/v1/usage/summary` 用量汇总接口
- 支持可选的业务方 API Key 认证
- 无 Redis 时使用进程内限流器，便于本地开发
- 提供 `/metrics` Prometheus 文本指标接口
- 提供健康检查、自动化测试和 Docker 镜像构建

## 运行方式

创建项目本地虚拟环境：

```powershell
python -m venv env
```

在 PowerShell 中激活虚拟环境：

```powershell
.\env\Scripts\Activate.ps1
```

安装开发依赖：

```powershell
pip install -r requirements-dev.txt
```

复制环境变量示例：

```powershell
Copy-Item .env.example .env
```

在 `.env` 中填写需要启用的供应商 API Key。未配置真实 Key 的供应商不会注册到模型列表：

```dotenv
DEEPSEEK_API_KEY=your-api-key-here
QWEN_API_KEY=your-api-key-here
```

真实 `.env` 已被 Git 忽略，禁止把 API Key 写入代码或提交到仓库。阿里云百炼 API Key 与调用地域必须一致，默认使用华北2（北京）地址。

本地调用账本默认写入 `.data/gateway.db`，不依赖 Redis 或 Docker。`MODEL_PRICING_JSON` 可按供应商最新价格配置每百万 Token 的输入和输出价格，未配置时仍会记录 Token，但成本显示为 `null`。

启用业务方认证时，配置逗号分隔的 `名称:Key`，例如：

```dotenv
GATEWAY_API_KEYS=ops:your-gateway-key,analytics:another-key
RATE_LIMIT_PER_MINUTE=60
MODEL_FALLBACKS_JSON={"deepseek-v4-pro":["deepseek-v4-flash"]}
```

调用时通过 `X-API-Key` 或 `Authorization: Bearer <Key>` 传递。未配置 `GATEWAY_API_KEYS` 时，认证默认关闭，便于本地测试。当前无 Redis 也能运行，但内存限流只在单进程有效，重启后计数清零；生产环境应替换为 Redis 限流实现。

`MODEL_FALLBACKS_JSON` 是故障降级配置的预留入口，明天继续完成普通响应和流式响应的统一降级策略。

启动本地服务：

```powershell
uvicorn app.main:app --reload
```

启动后访问 `http://127.0.0.1:8000/docs` 查看交互式 API 文档。

使用 Docker Compose 构建并启动：

```powershell
docker compose up --build
```

## 调用示例

调用模型。将 `model` 设置为 `mock-echo` 可进行无外部依赖测试，也可以设置为已配置的 DeepSeek 或千问模型：

```powershell
$body = @{
    model = "qwen3.6-flash"
    messages = @(
        @{ role = "user"; content = "分析服务器 CPU 告警" }
    )
} | ConvertTo-Json -Depth 4

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/v1/chat/completions" `
    -ContentType "application/json" `
    -Body $body
```

查询按供应商和模型汇总的调用量：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/v1/usage/summary"
```

## 常用命令

运行全部自动化测试：

```powershell
pytest
```

检查代码规范：

```powershell
ruff check .
```

运行本地 Mock 评测集（需先启动服务）：

```powershell
python scripts/evaluate.py --model mock-echo
```

查看 Prometheus 指标：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/metrics"
```

构建 Docker 镜像：

```powershell
docker build -t enterprise-llm-gateway:local .
```

## 目录结构

```text
app/                 FastAPI 应用、统一兼容层与模型供应商适配器
.data/               本地 SQLite 调用账本（自动生成，不提交）
evals/               JSONL 格式的离线评测数据集
scripts/             评测与运维脚本
tests/               API 自动化测试
.github/workflows/   GitHub Actions 持续集成配置
Dockerfile           容器镜像定义
compose.yaml         本地容器编排配置
```

## 开发记录

### 2026-07-17（周五）

- 初始化统一 LLM Gateway 项目
- 接入 Mock、DeepSeek V4 和阿里云百炼千问
- 支持普通调用、SSE 流式输出、模型注册和环境变量密钥管理
- 增加 Docker、GitHub Actions、中文 README 和基础自动化测试

### 2026-07-20（周一）

- 抽取 OpenAI 兼容供应商基础适配器
- 增加 SQLite 调用账本和 `/v1/usage/summary` 汇总接口
- 记录请求 ID、供应商、模型、状态、延迟、Token 和可选成本
- 修复带有本地真实模型配置时的模型列表测试
- 增加 SQLite 用量账本、业务方 API Key 认证和本地限流
- 增加 Prometheus 指标接口、Mock 离线评测脚本和 11 个自动化测试

### 2026-07-20（下班标记）

- 已验证无 Redis 时本地内存限流可运行
- 明日继续完善主模型失败后的普通/流式统一降级
- 当前改动已完成本地测试，待明日继续扩展后统一提交

## 后续计划

- 增加超时重试、熔断和备用模型降级
- 将内存限流替换为 Redis 分布式限流
- 将 SQLite 账本替换为 PostgreSQL，并接入 OpenTelemetry/Langfuse
- 扩充中文运维场景模型评测集和人工/LLM Judge 评分

## 作者

zentrix566

## 许可证

本项目采用 [MIT License](LICENSE)。
