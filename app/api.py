"""HTTP API 路由。"""

import json
import math
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core import get_settings
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
)

router = APIRouter()


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
    provider: ModelProvider,
    request: ChatCompletionRequest,
    completion_id: str,
    created: int,
) -> AsyncIterator[str]:
    """将供应商流式结果转换为 OpenAI 风格的 SSE 事件。"""

    async for content in provider.stream(request):
        payload = {
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
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

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
    request: ChatCompletionRequest,
) -> ChatCompletionResponse | StreamingResponse:
    """通过统一协议调用指定模型。"""

    provider = require_provider(request.model)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    if request.stream:
        return StreamingResponse(
            stream_completion(provider, request, completion_id, created),
            media_type="text/event-stream",
        )

    try:
        content = await provider.complete(request)
    except ProviderRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "provider_request_failed",
                "message": str(exc),
            },
        ) from exc
    prompt_text = "\n".join(message.content for message in request.messages)
    prompt_tokens = estimate_tokens(prompt_text)
    completion_tokens = estimate_tokens(content)

    return ChatCompletionResponse(
        id=completion_id,
        created=created,
        model=request.model,
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
