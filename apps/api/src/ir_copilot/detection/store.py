"""Small in-memory time-series store used by synthetic scenarios."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MetricPoint:
    timestamp: datetime
    value: float


class MetricsStore:
    """Append-only in-memory metric series with bounded window queries."""

    def __init__(self) -> None:
        self._series: dict[str, list[MetricPoint]] = defaultdict(list)

    def append(self, metric: str, timestamp: datetime, value: float) -> None:
        if not metric:
            raise ValueError("metric must not be empty")
        points = self._series[metric]
        point = MetricPoint(timestamp=timestamp, value=float(value))
        if points and timestamp < points[-1].timestamp:
            raise ValueError("points for a metric must be appended in timestamp order")
        points.append(point)

    def window(
        self,
        metric: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[MetricPoint]:
        points = self._series.get(metric, [])
        selected = [
            point
            for point in points
            if (start is None or point.timestamp >= start)
            and (end is None or point.timestamp <= end)
        ]
        return selected[-limit:] if limit is not None else selected

    def latest(self, metric: str) -> MetricPoint | None:
        points = self._series.get(metric, [])
        return points[-1] if points else None

    def metric_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._series))

    def clear(self) -> None:
        self._series.clear()
