"""调用用量账本测试。"""

from app.usage import UsageLedger, estimate_cost


def test_usage_ledger_records_and_summarizes(tmp_path) -> None:
    ledger = UsageLedger(str(tmp_path / "usage.db"))

    ledger.record(
        request_id="request-1",
        provider="deepseek",
        model="deepseek-v4-flash",
        status="success",
        latency_ms=120,
        prompt_tokens=10,
        completion_tokens=20,
        estimated_cost=0.0001,
    )
    ledger.record(
        request_id="request-2",
        provider="deepseek",
        model="deepseek-v4-flash",
        status="error",
        latency_ms=40,
        prompt_tokens=5,
        error_code="provider_request_failed",
    )

    summary = ledger.summary()

    assert summary == [
        {
            "consumer": "anonymous",
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "total_calls": 2,
            "success_calls": 1,
            "error_calls": 1,
            "prompt_tokens": 15,
            "completion_tokens": 20,
            "total_tokens": 35,
            "average_latency_ms": 80.0,
            "estimated_cost": 0.0001,
        }
    ]


def test_estimate_cost_uses_per_million_token_pricing() -> None:
    pricing = (
        '{"qwen3.6-flash": '
        '{"input_per_million": 1, "output_per_million": 2}}'
    )

    assert estimate_cost("qwen3.6-flash", 1000, 500, pricing) == 0.002
    assert estimate_cost("unknown-model", 1000, 500, pricing) is None
