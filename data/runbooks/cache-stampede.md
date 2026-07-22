# Cache Stampede

## Symptoms

- Cache miss rate spikes after key expiry and database load rises sharply.
- Requests for the same cold keys fan out and increase latency.

## Checks

1. Compare cache hits, key expiry timing, database query volume, and request fan-out.
2. Identify whether a deploy changed TTLs, invalidation, or cache-key construction.
3. Confirm request coalescing and stale-while-revalidate behavior.

## Mitigations

1. Enable an approved stale response or request-coalescing path.
2. Stagger TTL expiry for the affected key family through the normal change process.
3. Record the key pattern and demand profile in the incident draft.

## Escalation

Escalate to the cache owner when origin capacity or customer latency is at risk.
