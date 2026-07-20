"""网关 API 自动化测试。"""

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_list_models() -> None:
    response = client.get("/v1/models")

    assert response.status_code == 200
    assert {
        "id": "mock-echo",
        "object": "model",
        "owned_by": "zentrix566",
    } in response.json()["data"]


def test_chat_completion() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-echo",
            "messages": [{"role": "user", "content": "检查磁盘空间"}],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["object"] == "chat.completion"
    assert result["choices"][0]["message"]["content"] == (
        "Mock 模型收到：检查磁盘空间"
    )
    assert result["usage"]["total_tokens"] > 0


def test_stream_chat_completion() -> None:
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "mock-echo",
            "messages": [{"role": "user", "content": "分析 CPU 告警"}],
            "stream": True,
        },
    ) as response:
        events = [line for line in response.iter_lines() if line]

    assert response.status_code == 200
    assert events[-1] == "data: [DONE]"
    first_payload = json.loads(events[0].removeprefix("data: "))
    assert first_payload["object"] == "chat.completion.chunk"


def test_unknown_model() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "missing-model",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "model_not_found"


def test_usage_summary() -> None:
    response = client.get("/v1/usage/summary")

    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_metrics_contains_request_counter() -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "llm_gateway_requests_total" in response.text
