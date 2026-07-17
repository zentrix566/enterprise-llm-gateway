"""无需外部 API Key 的 Mock 模型。"""

from collections.abc import AsyncIterator

from app.providers.base import ModelProvider
from app.schemas import ChatCompletionRequest


class MockEchoProvider(ModelProvider):
    """回显最后一条用户消息，用于本地开发和自动化测试。"""

    model_id = "mock-echo"
    owner = "zentrix566"

    async def complete(self, request: ChatCompletionRequest) -> str:
        """生成确定性的 Mock 回答。"""

        user_content = next(
            (
                message.content
                for message in reversed(request.messages)
                if message.role == "user"
            ),
            request.messages[-1].content,
        )
        return f"Mock 模型收到：{user_content}"

    async def stream(self, request: ChatCompletionRequest) -> AsyncIterator[str]:
        """按短文本片段输出 Mock 回答。"""

        content = await self.complete(request)
        chunk_size = 8
        for start in range(0, len(content), chunk_size):
            yield content[start : start + chunk_size]

