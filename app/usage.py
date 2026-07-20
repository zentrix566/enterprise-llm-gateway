"""调用用量账本与汇总查询。"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class UsageLedger:
    """使用 SQLite 保存每次模型调用的最小审计信息。"""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    consumer TEXT NOT NULL DEFAULT 'anonymous',
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost REAL,
                    error_code TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_usage_created_at "
                "ON usage_records(created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_usage_model "
                "ON usage_records(model)"
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(usage_records)")
            }
            if "consumer" not in columns:
                connection.execute(
                    "ALTER TABLE usage_records ADD COLUMN consumer TEXT "
                    "NOT NULL DEFAULT 'anonymous'"
                )

    def record(
        self,
        *,
        request_id: str,
        consumer: str = "anonymous",
        provider: str,
        model: str,
        status: str,
        latency_ms: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        estimated_cost: float | None = None,
        error_code: str | None = None,
    ) -> None:
        """写入一条调用记录。"""

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO usage_records (
                    request_id, consumer, provider, model, status, latency_ms,
                    prompt_tokens, completion_tokens, total_tokens,
                    estimated_cost, error_code, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    consumer,
                    provider,
                    model,
                    status,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    prompt_tokens + completion_tokens,
                    estimated_cost,
                    error_code,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def summary(self) -> list[dict[str, object]]:
        """按供应商和模型汇总调用量。"""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    provider,
                    consumer,
                    model,
                    COUNT(*) AS total_calls,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)
                        AS success_calls,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END)
                        AS error_calls,
                    SUM(prompt_tokens) AS prompt_tokens,
                    SUM(completion_tokens) AS completion_tokens,
                    SUM(total_tokens) AS total_tokens,
                    AVG(latency_ms) AS average_latency_ms,
                    SUM(estimated_cost) AS estimated_cost
                FROM usage_records
                GROUP BY consumer, provider, model
                ORDER BY total_calls DESC, model ASC
                """
            ).fetchall()

        return [dict(row) for row in rows]


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    pricing_json: str,
) -> float | None:
    """按配置中的每百万 Token 价格估算调用成本。"""

    try:
        pricing = json.loads(pricing_json)
        model_price = pricing.get(model)
        if not isinstance(model_price, dict):
            return None
        input_price = float(model_price["input_per_million"])
        output_price = float(model_price["output_per_million"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    return (
        prompt_tokens * input_price + completion_tokens * output_price
    ) / 1_000_000
