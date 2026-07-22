# Disk Pressure

## Symptoms

- Disk utilization and IO wait rise; writes slow or fail as capacity approaches the limit.
- Logs may show filesystem-full or compaction failures.

## Checks

1. Identify the filesystem, largest directories, inode usage, and growth rate.
2. Check retention jobs, failed uploads, and recent log-volume changes.
3. Verify whether the affected volume serves critical state.

## Mitigations

1. Follow the approved retention and cleanup procedure with human approval.
2. Reduce nonessential log volume and prepare a reviewed capacity increase.
3. Preserve forensic data required for the active incident.

## Escalation

Escalate to the storage owner before the filesystem reaches the emergency threshold.
