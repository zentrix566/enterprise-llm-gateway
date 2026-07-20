"""认证和限流测试。"""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.limits import InMemoryRateLimiter
from app.security import ApiKeyAuthenticator


def make_request(headers: list[tuple[bytes, bytes]]) -> Request:
    """构造认证器测试所需的请求对象。"""

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
        }
    )


def test_api_key_authenticator_supports_named_keys() -> None:
    authenticator = ApiKeyAuthenticator("ops:test-secret")

    request = make_request([(b"x-api-key", b"test-secret")])

    assert authenticator.authenticate(request) == "ops"


def test_api_key_authenticator_rejects_invalid_key() -> None:
    authenticator = ApiKeyAuthenticator("ops:test-secret")
    request = make_request([(b"x-api-key", b"wrong-secret")])

    with pytest.raises(HTTPException) as error:
        authenticator.authenticate(request)

    assert error.value.status_code == 401


def test_rate_limiter_rejects_after_limit() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)

    assert limiter.check("ops") is None
    assert limiter.check("ops") is not None
