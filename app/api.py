"""HTTP API 路由。"""

import json
import math
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse

from app.core import get_settings
from app.limits import InMemoryRateLimiter
from app.metrics import MetricsCollector
from app.providers.base import ModelProvider, ProviderRequestError
from app.providers.registry import provider_registry
from app.schemas import (
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelInfo,
    ModelListResponse,
    TokenUsage,
    UsageSummaryResponse,
)
from app.security import get_authenticator
from app.usage import UsageLedger, estimate_cost

router = APIRouter()
settings = get_settings()
usage_ledger = UsageLedger(settings.usage_db_path)
authenticator = get_authenticator()
rate_limiter = InMemoryRateLimiter(settings.rate_limit_per_minute)
metrics = MetricsCollector()


def authorize_and_limit(request: Request) -> str:
    """完成 API Key 认证和本地限流，并返回业务方名称。"""

    consumer = authenticator.authenticate(request)
    retry_after = rate_limiter.check(consumer)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limit_exceeded",
                "message": "请求频率超过当前业务方限制",
            },
            headers={"Retry-After": str(int(retry_after))},
        )
    request.state.consumer = consumer
    return consumer


def estimate_tokens(text: str) -> int:
    """为 Mock 模型提供可重复的近似 Token 统计。"""

    return max(1, math.ceil(len(text) / 4))


def require_provider(model_id: str) -> ModelProvider:
    """获取模型适配器，不存在时返回统一的 404 错误。"""

    provider = provider_registry.get(model_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "model_not_found",
                "message": f"模型 {model_id} 未注册",
            },
        )
    return provider


def require_provider_chain(model_id: str) -> list[ModelProvider]:
    """根据配置返回主模型及其备用模型链路。"""

    primary = require_provider(model_id)
    try:
        fallback_config = json.loads(get_settings().model_fallbacks_json)
        fallback_ids = fallback_config.get(model_id, [])
    except (TypeError, ValueError, json.JSONDecodeError):
        fallback_ids = []

    if not isinstance(fallback_ids, list):
        fallback_ids = []
    providers = [primary]
    for fallback_id in fallback_ids:
        if not isinstance(fallback_id, str) or fallback_id == model_id:
            continue
        fallback = provider_registry.get(fallback_id)
        if fallback is not None:
            providers.append(fallback)
    return providers


@router.get("/health", tags=["系统"])
async def health() -> dict[str, str]:
    """返回服务健康状态和版本。"""

    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/v1/models", response_model=ModelListResponse, tags=["模型"])
async def list_models() -> ModelListResponse:
    """列出网关当前可用的模型。"""

    return ModelListResponse(
        data=[
            ModelInfo(id=provider.model_id, owned_by=provider.owner)
            for provider in provider_registry.list()
        ]
    )


async def stream_completion(
    providers: list[ModelProvider],
    request: ChatCompletionRequest,
    completion_id: str,
    created: int,
    request_id: str,
    consumer: str,
) -> AsyncIterator[str]:
    """将供应商流式结果转换为 OpenAI 风格的 SSE 事件。"""

    started_at = time.perf_counter()
    response_parts: list[str] = []
    prompt_text = "\n".join(message.content for message in request.messages)
    prompt_tokens = estimate_tokens(prompt_text)
    for provider in providers:
        try:
            async for content in provider.stream(request):
                response_parts.append(content)
                chunk_payload = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk_payload, ensure_ascii=False)}\n\n"
        except ProviderRequestError:
            usage_ledger.record(
                request_id=request_id,
                consumer=consumer,
                provider=provider.owner,
                model=request.model,
                status="error",
                latency_ms=round((time.perf_counter() - started_at) * 1000),
                prompt_tokens=prompt_tokens,
                error_code="provider_request_failed",
            )
            metrics.record(
                provider=provider.owner,
                model=request.model,
                status="error",
                latency_ms=round((time.perf_counter() - started_at) * 1000),
            )
            if response_parts:
                raise
            continue

        completion_tokens = estimate_tokens("".join(response_parts))
        usage_ledger.record(
            request_id=request_id,
            consumer=consumer,
            provider=provider.owner,
            model=request.model,
            status="success",
            latency_ms=round((time.perf_counter() - started_at) * 1000),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=estimate_cost(
                request.model,
                prompt_tokens,
                completion_tokens,
                get_settings().model_pricing_json,
            ),
        )
        metrics.record(
            provider=provider.owner,
            model=request.model,
            status="success",
            latency_ms=round((time.perf_counter() - started_at) * 1000),
        )
        break
    else:
        raise ProviderRequestError("所有备用模型均调用失败")
    metrics.record(
        provider=provider.owner,
        model=request.model,
        status="success",
        latency_ms=round((time.perf_counter() - started_at) * 1000),
    )
    final_payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": request.model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(final_payload, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@router.post(
    "/v1/chat/completions",
    tags=["聊天补全"],
    response_model=None,
)
async def create_chat_completion(
    payload: ChatCompletionRequest,
    request: Request,
) -> ChatCompletionResponse | StreamingResponse:
    """通过统一协议调用指定模型。"""

    providers = require_provider_chain(payload.model)
    provider = providers[0]
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    request_id = request.state.request_id
    consumer = authorize_and_limit(request)

    if payload.stream:
        return StreamingResponse(
            stream_completion(
                providers,
                payload,
                completion_id,
                created,
                request_id,
                consumer,
            ),
            media_type="text/event-stream",
        )

    started_at = time.perf_counter()
    prompt_text = "\n".join(message.content for message in payload.messages)
    prompt_tokens = estimate_tokens(prompt_text)
    try:
        content = await provider.complete(payload)
    except ProviderRequestError as exc:
        usage_ledger.record(
            request_id=request_id,
            consumer=consumer,
            provider=provider.owner,
            model=payload.model,
            status="error",
            latency_ms=round((time.perf_counter() - started_at) * 1000),
            prompt_tokens=prompt_tokens,
            error_code="provider_request_failed",
        )
        metrics.record(
            provider=provider.owner,
            model=payload.model,
            status="error",
            latency_ms=round((time.perf_counter() - started_at) * 1000),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "provider_request_failed",
                "message": str(exc),
            },
        ) from exc
    completion_tokens = estimate_tokens(content)
    usage_ledger.record(
        request_id=request_id,
        consumer=consumer,
        provider=provider.owner,
        model=payload.model,
        status="success",
        latency_ms=round((time.perf_counter() - started_at) * 1000),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=estimate_cost(
            payload.model,
            prompt_tokens,
            completion_tokens,
            get_settings().model_pricing_json,
        ),
    )
    metrics.record(
        provider=provider.owner,
        model=payload.model,
        status="success",
        latency_ms=round((time.perf_counter() - started_at) * 1000),
    )

    return ChatCompletionResponse(
        id=completion_id,
        created=created,
        model=payload.model,
        choices=[
            ChatCompletionChoice(
                message=ChatCompletionMessage(content=content),
            )
        ],
        usage=TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


@router.get(
    "/v1/usage/summary",
    response_model=UsageSummaryResponse,
    tags=["用量"],
)
async def usage_summary(request: Request) -> UsageSummaryResponse:
    """按供应商和模型返回调用量、Token 与成本汇总。"""

    authorize_and_limit(request)
    return UsageSummaryResponse(data=usage_ledger.summary())


@router.get("/metrics", tags=["监控"])
async def metrics_endpoint() -> Response:
    """返回 Prometheus 文本格式的进程内指标。"""

    return Response(content=metrics.render(), media_type="text/plain")
