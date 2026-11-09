"""Synthetic owner-managed authorization epochs; no identity service or I/O."""
from dataclasses import dataclass, replace
from day24_recovery import identifier, integer, validate, recover_rejected
from day25_authorization import SourcePolicy, recover_authorized

POLICY = 'day26-authorization-lifecycle-v1'


@dataclass(frozen=True)
class Lease:
    lease_id: str
    epoch: int
    not_before: int
    expires_at: int
    policy: SourcePolicy


@dataclass(frozen=True)
class Authority:
    epoch: int
    revoked: tuple[str, ...]


def lifecycle_reason(lease, authority, now):
    if (type(lease) is not Lease or type(authority) is not Authority
            or not identifier(lease.lease_id)
            or not integer(lease.epoch, 1, 2**53)
            or not integer(authority.epoch, 1, 2**53)
            or not integer(lease.not_before, 0, 2**53)
            or not integer(lease.expires_at, 0, 2**53)
            or lease.not_before >= lease.expires_at
            or type(lease.policy) is not SourcePolicy
            or type(authority.revoked) is not tuple
            or any(not identifier(x) for x in authority.revoked)
            or len(set(authority.revoked)) != len(authority.revoked)):
        return 'invalid_lifecycle'
    if lease.epoch != authority.epoch:
        return 'obsolete_lease_epoch'
    if lease.lease_id in authority.revoked:
        return 'revoked_lease'
    if not lease.not_before <= now < lease.expires_at:
        return 'inactive_lease'
    return None


def recover_with_lease(candidate, *, original, before, release_snapshot,
                       lease, release_lease, authority, release_authority):
    """Require fresh owner state at both checks and unchanged authority at release.

    Epochs must be durable, monotonic and independently obtained by the caller.
    Revocation requires a new epoch; renewing a lease requires a fresh ID.
    This pure function cannot detect replay of *all* trusted inputs or enforce
    single-use delivery. Hold an external lease through the final delivery.
    """
    reason = validate(before) or validate(release_snapshot)
    if reason is None:
        reason = (lifecycle_reason(lease, authority, before.now)
                  or lifecycle_reason(release_lease, release_authority, release_snapshot.now))
    if reason is None and (lease != release_lease or authority != release_authority):
        reason = 'lifecycle_changed'
    if reason:
        result = recover_rejected(candidate, original=original, before=None, release_snapshot=None)
        return replace(result, reason=reason, policy=POLICY)
    result = recover_authorized(candidate, original=original, before=before,
                                release_snapshot=release_snapshot, policy=lease.policy,
                                release_policy=release_lease.policy)
    return replace(result, policy=POLICY)
