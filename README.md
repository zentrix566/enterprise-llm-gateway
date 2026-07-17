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

## 常用命令

运行全部自动化测试：

```powershell
pytest
```

检查代码规范：

```powershell
ruff check .
```

构建 Docker 镜像：

```powershell
docker build -t enterprise-llm-gateway:local .
```

## 目录结构

```text
app/                 FastAPI 应用、统一兼容层与模型供应商适配器
tests/               API 自动化测试
.github/workflows/   GitHub Actions 持续集成配置
Dockerfile           容器镜像定义
compose.yaml         本地容器编排配置
```

## 后续计划

- 增加虚拟 API Key、限流和预算控制
- 增加超时重试、熔断和备用模型降级
- 接入 Prometheus、OpenTelemetry 和 Langfuse
- 建设中文运维场景模型评测集

## 作者

zentrix566

## 许可证

本项目采用 [MIT License](LICENSE)。
