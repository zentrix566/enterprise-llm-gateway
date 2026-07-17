"""OpenAI Chat Completions 兼容供应商基础适配器。"""

import json
from collections.abc import AsyncIterator

import httpx

from app.providers.base import ModelProvider, ProviderRequestError
from app.schemas import ChatCompletionRequest


class OpenAICompatibleProvider(ModelProvider):
    """复用 OpenAI 兼容供应商的普通与流式调用逻辑。"""

    def __init__(
        self,
        model_id: str,
        api_key: str,
        base_url: str,
        owner: str,
        provider_name: str,
        timeout_seconds: float = 120,
    ) -> None:
        self.model_id = model_id
        self.owner = owner
        self._provider_name = provider_name
        self._api_key = api_key
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._timeout = httpx.Timeout(timeout_seconds)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _payload(
        self,
        request: ChatCompletionRequest,
        *,
        stream: bool,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.model_id,
            "messages": [message.model_dump() for message in request.messages],
            "stream": stream,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    async def complete(self, request: ChatCompletionRequest) -> str:
        """返回一次完整的兼容模型回答。"""

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._endpoint,
                    headers=self._headers(),
                    json=self._payload(request, stream=False),
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderRequestError(
                f"{self._provider_name} 模型调用失败"
            ) from exc

        if not isinstance(content, str):
            raise ProviderRequestError(
                f"{self._provider_name} 返回了无法识别的内容"
            )
        return content

    async def stream(self, request: ChatCompletionRequest) -> AsyncIterator[str]:
        """逐段返回兼容供应商的 SSE 回答。"""

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    self._endpoint,
                    headers=self._headers(),
                    json=self._payload(request, stream=True),
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line.removeprefix("data: ")
                        if data == "[DONE]":
                            return
                        payload = json.loads(data)
                        content = payload["choices"][0]["delta"].get("content")
                        if content:
                            yield content
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderRequestError(
                f"{self._provider_name} 流式调用失败"
            ) from exc
