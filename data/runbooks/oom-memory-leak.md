# Memory Leak After Deploy

## Symptoms

- RSS climbs steadily after a deployment and does not return after garbage collection.
- GC pause duration increases, followed by OOM kills, latency, or error-rate growth.

## Checks

1. Compare RSS slope and heap profiles before and after the deployment timestamp.
2. Confirm whether replica restarts temporarily reset memory usage.
3. Identify allocation hot paths and retained object types in the approved profiler.

## Mitigations

1. Halt further rollout and use the normal rollback or capacity process after human approval.
2. Raise replica capacity only as a temporary, reviewed containment action.
3. Create a follow-up for the leaking allocation path and regression test.

## Escalation

Escalate to the service owner when memory approaches the container limit or an OOM kill occurs.
