# External API Rate Limit

## Symptoms

- External API calls receive 429 responses and `Retry-After` headers.
- Retry volume rises and dependent customer actions are delayed.

## Checks

1. Inspect provider limit headers, request volume, tenant distribution, and retry behavior.
2. Verify whether a recent client release increased request fan-out.
3. Confirm that backoff honors the provider's `Retry-After` value.

## Mitigations

1. Reduce noncritical requests and queue work using the approved service controls.
2. Apply documented backoff and request coalescing configuration after review.
3. Contact the provider if contractual quota is exhausted.

## Escalation

Escalate to the integration owner for sustained customer impact or quota changes.
