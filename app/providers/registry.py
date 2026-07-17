"""模型注册表。"""

from app.providers.base import ModelProvider
from app.providers.mock import MockEchoProvider


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


provider_registry = ProviderRegistry([MockEchoProvider()])

