"""Closed-contract recovery from owner-controlled synthetic incident records."""
from dataclasses import dataclass


@dataclass(frozen=True)
class FactRecord:
    incident_id: str
    source_id: str
    revision: int
    duration_minutes: int
    recovery: str


RECOVERY = {
    "database_restart": "restarting the database",
    "queue_rollback": "rolling back the queue configuration",
    "cache_failover": "failing over to the standby cache",
}


@dataclass(frozen=True)
class Outcome:
    status: str
    text: str | None
    contained: bool
    reasons: tuple[str, ...]
    provenance: tuple[tuple[str, int], ...]


def render(record):
    return (f"The application was unavailable for {record.duration_minutes} minutes, "
            f"and engineers restored service by {RECOVERY[record.recovery]}.")


def release_or_recover(candidate, *, incident_id, records=(), approved_sources=()):
    """Both records and source approvals must arrive through the trusted owner path.

    Source names are allowlist references, not authentication. Never construct
    either argument from retrieved documents or candidate verification claims.
    Multiple applicable records must agree; revisions never silently win.
    """
    def abstain(reason):
        return Outcome("abstained", None, True, (reason,), ())

    if type(incident_id) is not str or not incident_id:
        return abstain("invalid_incident")
    if type(records) is not tuple or type(approved_sources) is not tuple:
        return abstain("invalid_trusted_input")
    if any(type(s) is not str or not s for s in approved_sources):
        return abstain("invalid_source_approval")
    # Malformed entries cannot be silently ignored as if no conflict existed.
    if any(type(r) is not FactRecord for r in records):
        return abstain("invalid_record")
    selected = [r for r in records if r.incident_id == incident_id]
    if not selected:
        return abstain("missing_facts")
    for r in selected:
        if (type(r.source_id) is not str or r.source_id not in approved_sources
                or type(r.revision) is not int or r.revision < 1
                or type(r.duration_minutes) is not int or r.duration_minutes < 1
                or type(r.recovery) is not str or r.recovery not in RECOVERY):
            return abstain("invalid_or_unapproved_facts")
    if len({(r.duration_minutes, r.recovery) for r in selected}) != 1:
        return abstain("conflicting_facts")
    text = render(selected[0])
    provenance = tuple(sorted({(r.source_id, r.revision) for r in selected}))
    # Exact matching is deliberately conservative: no unsupported suffixes,
    # URLs, cross-incident facts, or arbitrary paraphrases are released.
    if type(candidate) is str and candidate == text:
        return Outcome("released", text, False, (), provenance)
    return Outcome("recovered", text, True, ("outside_output_contract",), provenance)
