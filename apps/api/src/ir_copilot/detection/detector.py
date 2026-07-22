"""Pure, deterministic anomaly detection. This module has no LLM dependencies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, median, pstdev
from typing import Any

from .store import MetricsStore


@dataclass(frozen=True)
class MetricSignal:
    metric: str
    value: float
    z_score: float
    percent_change: float
    method: str


@dataclass(frozen=True)
class AnomalyResult:
    is_anomalous: bool
    severity: str
    metric: str | None
    score: float
    method: str | None
    window_start: str | None
    window_end: str | None
    related_metrics: dict[str, float]
    rule_id: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class AnomalyDetector:
    """Evaluate only the newest metric values against their preceding window."""

    def __init__(
        self,
        *,
        rolling_window: int = 30,
        zscore_threshold: float = 3.0,
        percent_change_threshold: float = 2.0,
        epsilon: float = 1e-9,
    ) -> None:
        if rolling_window < 2:
            raise ValueError("rolling_window must be at least 2")
        self.rolling_window = rolling_window
        self.zscore_threshold = zscore_threshold
        self.percent_change_threshold = percent_change_threshold
        self.epsilon = epsilon

    def evaluate(self, store: MetricsStore) -> AnomalyResult:
        signals = self._signals(store)
        return self._select_result(store, signals)

    def _signals(self, store: MetricsStore) -> dict[str, MetricSignal]:
        signals: dict[str, MetricSignal] = {}
        for metric in store.metric_names():
            points = store.window(metric, limit=self.rolling_window + 1)
            if len(points) < self.rolling_window + 1:
                continue
            baseline = [point.value for point in points[:-1]]
            value = points[-1].value
            baseline_mean = mean(baseline)
            baseline_std = pstdev(baseline)
            z_score = abs(value - baseline_mean) / max(baseline_std, self.epsilon)
            baseline_median = median(baseline)
            percent_change = (value - baseline_median) / max(abs(baseline_median), self.epsilon)
            method = self._signal_method(metric, z_score, percent_change)
            signals[metric] = MetricSignal(metric, value, z_score, percent_change, method)
        return signals

    def _signal_method(self, metric: str, z_score: float, percent_change: float) -> str:
        percent_threshold = 0.5 if metric == "rss" else self.percent_change_threshold
        zscore_hit = z_score > self.zscore_threshold
        percent_hit = percent_change > percent_threshold
        if zscore_hit and percent_hit:
            return "zscore_and_percent_change"
        if zscore_hit:
            return "zscore"
        if percent_hit:
            return "percent_change"
        return "none"

    def _select_result(
        self, store: MetricsStore, signals: dict[str, MetricSignal]
    ) -> AnomalyResult:
        related = {metric: signal.value for metric, signal in signals.items()}
        active = [signal for signal in signals.values() if signal.method != "none"]
        if not active:
            return self._result(False, "none", None, store, related, None)

        error = signals.get("error_rate")
        db_pool = signals.get("db_pool_util")
        if error and db_pool and error.z_score > self.zscore_threshold and db_pool.value >= 0.9:
            return self._result(True, "high", error, store, related, "rule.db_pool_saturation")

        rss = signals.get("rss")
        gc_pause = signals.get("gc_pause")
        if rss and gc_pause and rss.percent_change > 0.5 and gc_pause.z_score > self.zscore_threshold:
            return self._result(True, "high", rss, store, related, "rule.memory_leak")

        latency = signals.get("latency_p95")
        if latency and latency.z_score > self.zscore_threshold and latency.percent_change > 2.0:
            return self._result(True, "high", latency, store, related, "rule.latency_regression")

        dependency = signals.get("dependency_error_rate")
        cpu = signals.get("cpu_util")
        if dependency and dependency.z_score > self.zscore_threshold and (
            cpu is None or cpu.method == "none"
        ):
            return self._result(True, "high", dependency, store, related, "rule.upstream_dependency")

        strongest = max(active, key=lambda signal: max(signal.z_score, signal.percent_change))
        return self._result(True, "low", strongest, store, related, "rule.single_metric_signal")

    def _result(
        self,
        is_anomalous: bool,
        severity: str,
        signal: MetricSignal | None,
        store: MetricsStore,
        related: dict[str, float],
        rule_id: str | None,
    ) -> AnomalyResult:
        timestamps = [
            point.timestamp
            for metric in store.metric_names()
            for point in store.window(metric, limit=self.rolling_window + 1)
        ]
        return AnomalyResult(
            is_anomalous=is_anomalous,
            severity=severity,
            metric=signal.metric if signal else None,
            score=round(signal.z_score if signal else 0.0, 4),
            method=signal.method if signal else None,
            window_start=min(timestamps).isoformat() if timestamps else None,
            window_end=max(timestamps).isoformat() if timestamps else None,
            related_metrics=related,
            rule_id=rule_id,
        )
