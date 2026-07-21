"""无外部依赖的本地限流器。"""

import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    """按业务方在固定时间窗口内限制请求数。"""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> float | None:
        """允许请求时返回 None，否则返回建议等待秒数。"""

        now = time.monotonic()
        timestamps = self._requests[key]
        threshold = now - self.window_seconds
        while timestamps and timestamps[0] <= threshold:
            timestamps.popleft()

        if len(timestamps) >= self.limit:
            return max(1.0, self.window_seconds - (now - timestamps[0]))

        timestamps.append(now)
        return None
