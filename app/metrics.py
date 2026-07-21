"""无需外部依赖的 Prometheus 文本指标。"""

from collections import defaultdict


class MetricsCollector:
    """在进程内聚合请求计数和延迟，兼容 Prometheus 抓取格式。"""

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str, str], int] = defaultdict(int)
        self._latency_seconds: dict[tuple[str, str], float] = defaultdict(float)

    def record(
        self,
        *,
        provider: str,
        model: str,
        status: str,
        latency_ms: int,
    ) -> None:
        """记录一次模型请求指标。"""

        key = (provider, model, status)
        self._counts[key] += 1
        self._latency_seconds[(provider, model)] += latency_ms / 1000

    @staticmethod
    def _label(value: str) -> str:
        """转义 Prometheus 标签值。"""

        return value.replace("\\", "\\\\").replace('"', '\\"')

    def render(self) -> str:
        """生成 Prometheus exposition 文本。"""

        lines = [
            "# HELP llm_gateway_requests_total 模型请求总数",
            "# TYPE llm_gateway_requests_total counter",
        ]
        for (provider, model, status), count in sorted(self._counts.items()):
            labels = (
                f'provider="{self._label(provider)}",'
                f'model="{self._label(model)}",status="{self._label(status)}"'
            )
            lines.append(f"llm_gateway_requests_total{{{labels}}} {count}")

        lines.extend(
            [
                "# HELP llm_gateway_request_latency_seconds_sum 模型请求耗时总和",
                "# TYPE llm_gateway_request_latency_seconds_sum counter",
            ]
        )
        for (provider, model), latency in sorted(self._latency_seconds.items()):
            labels = (
                f'provider="{self._label(provider)}",'
                f'model="{self._label(model)}"'
            )
            lines.append(
                f"llm_gateway_request_latency_seconds_sum{{{labels}}} {latency}"
            )
        return "\n".join(lines) + "\n"
