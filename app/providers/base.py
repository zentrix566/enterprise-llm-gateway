"""模型供应商统一抽象。"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.schemas import ChatCompletionRequest


class ModelProvider(ABC):
    """所有模型供应商必须实现的统一接口。"""

    model_id: str
    owner: str

    @abstractmethod
    async def complete(self, request: ChatCompletionRequest) -> str:
        """返回一次完整的模型回答。"""

    @abstractmethod
    async def stream(self, request: ChatCompletionRequest) -> AsyncIterator[str]:
        """逐段返回模型回答。"""
        if False:
            yield ""

