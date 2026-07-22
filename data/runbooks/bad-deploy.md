# Regressive Deploy and Latency Regression

## Symptoms

- p95 latency steps up immediately after a deployment or feature flag change.
- Error rate may rise while CPU and dependency health remain near baseline.

## Checks

1. Correlate the latency step with the deploy SHA, release time, and feature-flag changes.
2. Compare endpoint latency and error rate with the previous release.
3. Check canary versus stable instances before assigning root cause.

## Mitigations

1. Pause rollout and prepare the approved rollback procedure for human review.
2. Disable the implicated feature flag through the change-management process.
3. Draft a regression issue with the release identifier and affected endpoints.

## Escalation

Escalate to the release owner if customer latency remains above the service objective for five minutes.
