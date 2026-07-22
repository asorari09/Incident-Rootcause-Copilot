# CPU Throttle and Saturation

## Symptoms

- CPU utilization, throttled seconds, and request latency rise together.
- Queue depth grows while dependency error rate remains normal.

## Checks

1. Compare requested CPU, limits, throttling counters, and runnable queue depth.
2. Identify a traffic or workload change before changing resource settings.
3. Confirm that database and dependency latency are not the primary bottleneck.

## Mitigations

1. Apply approved traffic shedding for noncritical work.
2. Prepare a reviewed resource request or capacity adjustment; do not mutate infrastructure automatically.
3. Profile the hot endpoint before making permanent sizing changes.

## Escalation

Escalate to the platform owner when throttling affects a critical service objective.
