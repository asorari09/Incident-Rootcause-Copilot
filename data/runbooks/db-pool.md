# Database Connection Pool Exhaustion

## Symptoms

- API error rate rises with `timeout acquiring database connection` messages.
- `db_pool_util` remains above 0.90 and p95 latency climbs.

## Checks

1. Confirm pool utilization, wait time, and active versus idle connections.
2. Compare request volume with the configured pool size and database connection limit.
3. Check for long-running queries or a deploy that stopped connections returning to the pool.

## Mitigations

1. Reduce nonessential traffic and protect critical endpoints with rate limits.
2. Cancel confirmed runaway queries only through the approved database procedure.
3. Prepare a reviewed pool-size or connection-lifetime change; do not apply it automatically.

## Escalation

Escalate to the database owner when utilization stays above 90% for ten minutes or errors affect customer writes.
