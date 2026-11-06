from __future__ import annotations

from community_llm_protocol import JobStatus

ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.ASSIGNED, JobStatus.CANCELLED, JobStatus.EXPIRED}),
    JobStatus.ASSIGNED: frozenset(
        {
            JobStatus.RUNNING,
            JobStatus.FAILED,
            JobStatus.EXPIRED,
            JobStatus.CANCELLED,
        }
    ),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.UPLOADED,
            JobStatus.FAILED,
            JobStatus.EXPIRED,
            JobStatus.CANCELLED,
        }
    ),
    JobStatus.UPLOADED: frozenset({JobStatus.VERIFIED, JobStatus.REJECTED}),
    JobStatus.VERIFIED: frozenset({JobStatus.PAID}),
    JobStatus.PAID: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.REJECTED: frozenset(),
    JobStatus.EXPIRED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}


class InvalidJobTransition(ValueError):
    def __init__(self, current: JobStatus, requested: JobStatus) -> None:
        super().__init__(f"cannot transition job from {current.value} to {requested.value}")
        self.current = current
        self.requested = requested


def can_transition(current: JobStatus | str, requested: JobStatus | str) -> bool:
    current_status = JobStatus(current)
    requested_status = JobStatus(requested)
    return requested_status in ALLOWED_TRANSITIONS[current_status]


def assert_transition(current: JobStatus | str, requested: JobStatus | str) -> None:
    if not can_transition(current, requested):
        raise InvalidJobTransition(JobStatus(current), JobStatus(requested))
