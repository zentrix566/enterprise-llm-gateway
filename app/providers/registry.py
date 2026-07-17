"""模型注册表。"""

from app.core import get_settings
from app.providers.base import ModelProvider
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockEchoProvider
from app.providers.qwen import QwenProvider


class ProviderRegistry:
    """集中管理模型标识与供应商适配器的映射。"""

    def __init__(self, providers: list[ModelProvider]) -> None:
        self._providers = {provider.model_id: provider for provider in providers}

    def get(self, model_id: str) -> ModelProvider | None:
        """按模型标识查找供应商。"""

        return self._providers.get(model_id)

    def list(self) -> list[ModelProvider]:
        """返回全部已注册供应商。"""

        return list(self._providers.values())


def build_providers() -> list[ModelProvider]:
    """根据本地配置创建可用的模型适配器。"""

    settings = get_settings()
    providers: list[ModelProvider] = [MockEchoProvider()]
    if settings.deepseek_api_key is not None:
        deepseek_api_key = settings.deepseek_api_key.get_secret_value().strip()
        if deepseek_api_key and deepseek_api_key != "your-api-key-here":
            deepseek_model_ids = {
                model_id.strip()
                for model_id in settings.deepseek_models.split(",")
                if model_id.strip()
            }
            providers.extend(
                DeepSeekProvider(
                    model_id=model_id,
                    api_key=deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                )
                for model_id in sorted(deepseek_model_ids)
            )

    if settings.qwen_api_key is not None:
        qwen_api_key = settings.qwen_api_key.get_secret_value().strip()
        if qwen_api_key and qwen_api_key != "your-api-key-here":
            qwen_model_ids = {
                model_id.strip()
                for model_id in settings.qwen_models.split(",")
                if model_id.strip()
            }
            providers.extend(
                QwenProvider(
                    model_id=model_id,
                    api_key=qwen_api_key,
                    base_url=settings.qwen_base_url,
                )
                for model_id in sorted(qwen_model_ids)
            )

    return providers


provider_registry = ProviderRegistry(build_providers())
