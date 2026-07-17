"""阿里云百炼千问 OpenAI 兼容接口适配器。"""

from app.providers.openai_compatible import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    """通过阿里云百炼 Chat Completions API 调用千问模型。"""

    def __init__(
        self,
        model_id: str,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 120,
    ) -> None:
        super().__init__(
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            owner="alibaba-cloud",
            provider_name="千问",
            timeout_seconds=timeout_seconds,
        )
