"""OpenAI 兼容接口所需的数据模型。"""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """一条对话消息。"""

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    """聊天补全请求。"""

    model: str
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)


class ChatCompletionMessage(BaseModel):
    """聊天补全返回消息。"""

    role: Literal["assistant"] = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    """聊天补全候选结果。"""

    index: int = 0
    message: ChatCompletionMessage
    finish_reason: Literal["stop", "length"] = "stop"


class TokenUsage(BaseModel):
    """一次模型调用的 Token 用量。"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI 风格的聊天补全响应。"""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: TokenUsage


class ModelInfo(BaseModel):
    """网关公开的模型信息。"""

    id: str
    object: Literal["model"] = "model"
    owned_by: str


class ModelListResponse(BaseModel):
    """模型列表响应。"""

    object: Literal["list"] = "list"
    data: list[ModelInfo]


class UsageSummaryItem(BaseModel):
    """单个供应商模型的用量汇总。"""

    consumer: str
    provider: str
    model: str
    total_calls: int
    success_calls: int
    error_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    average_latency_ms: float | None
    estimated_cost: float | None


class UsageSummaryResponse(BaseModel):
    """网关调用用量汇总响应。"""

    data: list[UsageSummaryItem]
