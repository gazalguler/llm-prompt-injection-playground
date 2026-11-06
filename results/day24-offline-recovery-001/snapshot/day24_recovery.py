"""Offline owner-controlled recovery. All Snapshot inputs are TRUSTED adapter output.

This module checks consistency, not credentials or signatures. An authenticated
application must bind the principal, task, records and current pins independently
of model/tool text, and hold its authorization/revision lease through delivery.
No I/O, extraction, model repair, arbitrary templates or candidate release path.
"""
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import re
from day21_gate import Decision

POLICY = "day24-incident-v1"
TEMPLATE = "incident-duration-restoration-v1"
TASK = "incident_duration_and_restoration"
COMPONENTS = ("database", "cache", "worker")


@dataclass(frozen=True)
class Record:
    record_id: str
    source_id: str
    schema: int
    revision: int
    observed_at: int
    duration_minutes: int
    component: str
    relation: str


@dataclass(frozen=True)
class Pin:
    record_id: str
    source_id: str
    schema: int
    revision: int
    record_sha256: str
    # Adapter's verified provenance reference, never a claim read from a tool.
    provenance: str
    authenticated: bool


@dataclass(frozen=True)
class Snapshot:
    principal: str
    authorized: bool
    task: str
    record_id: str
    now: int
    expires_at: int
    max_age: int
    records: tuple[Record, ...]
    pins: tuple[Pin, ...]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def record_digest(record):
    return digest(asdict(record))


def identifier(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._-]{0,95}", value) is not None


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def validate(s):
    if type(s) is not Snapshot:
        return "invalid_snapshot"
    if not identifier(s.principal) or s.authorized is not True:
        return "unauthorized"
    if type(s.task) is not str or s.task != TASK or not identifier(s.record_id):
        return "unsupported_task_or_identity"
    if (not integer(s.now, 0, 2**53) or not integer(s.expires_at, 0, 2**53)
            or not integer(s.max_age, 1, 86400) or s.now >= s.expires_at):
        return "invalid_or_expired_authorization"
    if (type(s.records) is not tuple or type(s.pins) is not tuple
            or not 1 <= len(s.records) <= 16 or len(s.records) != len(s.pins)):
        return "missing_or_ambiguous_sources"
    if any(type(r) is not Record for r in s.records) or any(type(p) is not Pin for p in s.pins):
        return "invalid_typed_input"
    sources = set()
    for r, p in zip(s.records, s.pins):
        if (not identifier(r.record_id) or r.record_id != s.record_id
                or not identifier(r.source_id) or r.source_id in sources):
            return "wrong_or_duplicate_identity"
        sources.add(r.source_id)
        if (not integer(r.schema, 1, 1) or not integer(r.revision, 1, 2**31)
                or not integer(r.observed_at, 0, 2**53)
                or not integer(r.duration_minutes, 1, 9999)
                or type(r.component) is not str or r.component not in COMPONENTS
                or type(r.relation) is not str or r.relation != "restart_restored_service"):
            return "invalid_or_unsupported_facts"
        if r.observed_at > s.now or s.now - r.observed_at > s.max_age:
            return "stale_or_future_facts"
        if (p.authenticated is not True or not identifier(p.provenance)
                or type(p.record_id) is not str or type(p.source_id) is not str
                or not integer(p.schema, 1, 1) or not integer(p.revision, 1, 2**31)
                or (p.record_id, p.source_id, p.schema, p.revision)
                != (r.record_id, r.source_id, r.schema, r.revision)
                or type(p.record_sha256) is not str or p.record_sha256 != record_digest(r)):
            return "unauthenticated_or_unpinned_record"
    if len({(r.duration_minutes, r.component, r.relation) for r in s.records}) != 1:
        return "conflicting_facts"
    return None


@dataclass(frozen=True)
class Outcome:
    released: bool
    text: str | None
    reason: str
    eligible: bool
    candidate_sha256: str | None
    original_reasons: tuple[str, ...]
    snapshot_sha256: str | None
    provenance: tuple[tuple[str, int, str], ...]
    policy: str = POLICY
    template: str = TEMPLATE


def recover_rejected(candidate, *, original, before, release_snapshot):
    """Two-phase check; release_snapshot is re-read by trusted code under a lease.

    Callers must serialize final check and delivery against revocation/revision
    changes. Two supplied snapshots alone do not eliminate a post-check race.
    Candidate bytes are hashed for audit only; none become rendered facts.
    """
    candidate_hash = hashlib.sha256(candidate.encode('utf-8', errors='surrogatepass')).hexdigest() if type(candidate) is str else None
    reasons = original.reasons if type(original) is Decision else ()

    def stop(reason, eligible=False):
        return Outcome(False, None, reason, eligible, candidate_hash, reasons, None, ())

    if (type(original) is not Decision or original.released is not False
            or original.text is not None or type(reasons) is not tuple
            or not reasons or any(type(x) is not str for x in reasons)):
        return stop("requires_discarded_candidate")
    reason = validate(before)
    if reason:
        return stop(reason)
    reason = validate(release_snapshot)
    if reason:
        return stop("release_" + reason, True)
    if release_snapshot.now < before.now or replace(release_snapshot, now=before.now) != before:
        return stop("snapshot_changed", True)
    r = before.records[0]
    # All slots are bounded integers or finite owner-defined identifiers.
    text = (f"System-rendered incident summary: The application was unavailable for "
            f"{r.duration_minutes} minutes, and service was restored by restarting the {r.component}.")
    provenance = tuple((p.source_id, p.revision, p.provenance) for p in before.pins)
    return Outcome(True, text, "recovered", True, candidate_hash, reasons,
                   digest(asdict(before)), provenance)
