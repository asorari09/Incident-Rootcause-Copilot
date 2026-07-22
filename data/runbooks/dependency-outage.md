# Upstream Dependency Outage

## Symptoms

- `dependency_error_rate` and downstream 503 responses rise while local CPU stays flat.
- Application errors cluster around calls to one upstream service.

## Checks

1. Compare dependency status, timeout rate, and retry volume with local CPU and saturation.
2. Inspect the provider status page and recent dependency incident notices.
3. Verify circuit-breaker and fallback behavior without increasing retry storms.

## Mitigations

1. Enable an approved cached or degraded response path if one already exists.
2. Reduce retries and use backoff according to the service client policy.
3. Communicate impact and link the upstream incident in the customer-facing draft issue.

## Escalation

Escalate to the dependency owner when 503s persist beyond the retry budget or critical requests fail.
