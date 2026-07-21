"""FastAPI 应用入口。"""

import uuid

from fastapi import FastAPI, Request

from app.api import router
from app.core import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="提供统一模型协议、路由和治理能力的企业级 LLM 网关。",
)
app.include_router(router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """为每个请求生成或透传关联标识。"""

    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
