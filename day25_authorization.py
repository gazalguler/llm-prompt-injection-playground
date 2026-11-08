"""Offline trusted-policy consistency checks; no credential authentication.

Policy and snapshots must come from independent owner-controlled application
code, never a candidate or retrieved document. Hold a lease through delivery.
"""
from dataclasses import dataclass, replace
from day24_recovery import TASK, identifier, integer, recover_rejected, validate

POLICY = "day25-source-authorization-v1"


@dataclass(frozen=True)
class Grant:
    principal: str
    task: str
    record_id: str
    source_id: str
    revision: int
    record_sha256: str
    provenance: str


@dataclass(frozen=True)
class SourcePolicy:
    grants: tuple[Grant, ...]


def authorized(snapshot, policy):
    if type(policy) is not SourcePolicy or type(policy.grants) is not tuple or not policy.grants:
        return False
    if any(type(g) is not Grant for g in policy.grants):
        return False
    for g in policy.grants:
        if (not all(identifier(v) for v in (g.principal, g.record_id, g.source_id, g.provenance))
                or type(g.task) is not str or g.task != TASK
                or not integer(g.revision, 1, 2**31)
                or type(g.record_sha256) is not str or len(g.record_sha256) != 64
                or any(c not in '0123456789abcdef' for c in g.record_sha256)):
            return False
    # Duplicate grants are ambiguous, even if their values happen to agree.
    keys = [(g.principal, g.task, g.record_id, g.source_id) for g in policy.grants]
    if len(set(keys)) != len(keys):
        return False
    return all(Grant(snapshot.principal, snapshot.task, snapshot.record_id,
                     p.source_id, p.revision, p.record_sha256, p.provenance)
               in policy.grants for p in snapshot.pins)


def recover_authorized(candidate, *, original, before, release_snapshot,
                       policy, release_policy):
    """Recheck owner policy and Day 24 snapshot before deterministic release.

    Exact revision/digest grants are synthetic authorization assertions, not
    signatures or evidence that facts are true. No real identity service exists.
    """
    reason = validate(before) or validate(release_snapshot)
    if reason is None:
        if not authorized(before, policy) or not authorized(release_snapshot, release_policy):
            reason = 'source_not_authorized'
        elif policy != release_policy:
            reason = 'source_policy_changed'
    if reason:
        denied = recover_rejected(candidate, original=original, before=None,
                                  release_snapshot=None)
        return replace(denied, reason=reason, policy=POLICY)
    return replace(recover_rejected(candidate, original=original, before=before,
                                   release_snapshot=release_snapshot), policy=POLICY)
