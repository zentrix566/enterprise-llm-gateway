"""本地 API Key 认证。"""

import hmac

from fastapi import HTTPException, Request, status

from app.core import get_settings


class ApiKeyAuthenticator:
    """从环境变量解析并校验业务方 API Key。"""

    def __init__(self, raw_keys: str | None) -> None:
        self._keys: dict[str, str] = {}
        for item in (raw_keys or "").split(","):
            item = item.strip()
            if not item:
                continue
            if ":" in item:
                name, key = item.split(":", maxsplit=1)
            else:
                name, key = "default", item
            if name.strip() and key.strip():
                self._keys[name.strip()] = key.strip()

    @property
    def enabled(self) -> bool:
        """返回是否配置了至少一个业务方 Key。"""

        return bool(self._keys)

    def authenticate(self, request: Request) -> str:
        """校验请求并返回业务方名称。"""

        if not self.enabled:
            return "anonymous"

        provided_key = request.headers.get("X-API-Key", "")
        if not provided_key:
            authorization = request.headers.get("Authorization", "")
            if authorization.lower().startswith("bearer "):
                provided_key = authorization[7:].strip()

        for name, expected_key in self._keys.items():
            if hmac.compare_digest(provided_key, expected_key):
                return name

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_api_key",
                "message": "缺少有效的业务方 API Key",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_authenticator() -> ApiKeyAuthenticator:
    """根据运行时配置返回认证器。"""

    settings = get_settings()
    raw_keys = (
        settings.gateway_api_keys.get_secret_value()
        if settings.gateway_api_keys is not None
        else None
    )
    return ApiKeyAuthenticator(raw_keys)
