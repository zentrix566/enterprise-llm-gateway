"""模型注册表配置测试。"""

from pytest import MonkeyPatch

from app.core import get_settings
from app.providers.registry import build_providers


def test_registry_only_has_mock_without_deepseek_key(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "your-api-key-here")
    monkeypatch.setenv("QWEN_API_KEY", "your-api-key-here")
    get_settings.cache_clear()

    providers = build_providers()

    assert [provider.model_id for provider in providers] == ["mock-echo"]
    get_settings.cache_clear()


def test_registry_adds_configured_deepseek_models(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("QWEN_API_KEY", "your-api-key-here")
    monkeypatch.setenv(
        "DEEPSEEK_MODELS",
        "deepseek-v4-pro,deepseek-v4-flash",
    )
    get_settings.cache_clear()

    providers = build_providers()

    assert [provider.model_id for provider in providers] == [
        "mock-echo",
        "deepseek-v4-flash",
        "deepseek-v4-pro",
    ]
    get_settings.cache_clear()


def test_registry_adds_configured_qwen_models(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "your-api-key-here")
    monkeypatch.setenv("QWEN_API_KEY", "test-key")
    monkeypatch.setenv(
        "QWEN_MODELS",
        "qwen3.7-plus,qwen3.6-flash",
    )
    get_settings.cache_clear()

    providers = build_providers()

    assert [provider.model_id for provider in providers] == [
        "mock-echo",
        "qwen3.6-flash",
        "qwen3.7-plus",
    ]
    get_settings.cache_clear()
