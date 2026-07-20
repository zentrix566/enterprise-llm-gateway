"""应用配置与日志初始化。"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量加载网关配置。"""

    app_name: str = "Enterprise LLM Gateway"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_models: str = "deepseek-v4-flash,deepseek-v4-pro"
    qwen_api_key: SecretStr | None = None
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_models: str = "qwen3.7-plus,qwen3.6-flash"
    usage_db_path: str = ".data/gateway.db"
    model_pricing_json: str = "{}"
    gateway_api_keys: SecretStr | None = None
    rate_limit_per_minute: int = Field(default=60, gt=0)
    model_fallbacks_json: str = "{}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """返回进程内复用的配置实例。"""

    return Settings()
