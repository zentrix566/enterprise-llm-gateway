"""运行本地模型网关的 JSONL 离线评测。"""

import argparse
import json
from pathlib import Path

import httpx


def evaluate_case(
    client: httpx.Client,
    base_url: str,
    model: str,
    case: dict[str, object],
) -> bool:
    """执行单条评测用例并返回是否通过。"""

    response = client.post(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": case["input"]}],
        },
    )
    if response.status_code != 200:
        return False

    content = response.json()["choices"][0]["message"]["content"]
    expected = case.get("expected_contains", [])
    return all(fragment in content for fragment in expected)


def main() -> int:
    """读取评测集并输出可复现的 JSON 汇总。"""

    parser = argparse.ArgumentParser(description="运行 LLM Gateway 离线评测")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default="mock-echo")
    parser.add_argument("--dataset", default="evals/smoke.jsonl")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    cases = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    with httpx.Client(timeout=60) as client:
        results = [
            evaluate_case(client, args.base_url, args.model, case)
            for case in cases
        ]

    passed = sum(results)
    total = len(results)
    print(
        json.dumps(
            {
                "model": args.model,
                "dataset": str(dataset_path),
                "passed": passed,
                "total": total,
                "pass_rate": passed / total if total else 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
