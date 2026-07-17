"""DeepSeek OpenAI 兼容接口适配器。"""

from app.providers.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """通过 DeepSeek Chat Completions API 调用指定模型。"""

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
            owner="deepseek",
            provider_name="DeepSeek",
            timeout_seconds=timeout_seconds,
        )
