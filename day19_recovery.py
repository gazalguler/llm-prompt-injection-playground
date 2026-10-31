"""Offline recovery with owner-pinned source, incident and revision bindings."""
from dataclasses import dataclass

from day18_recovery import FactRecord, Outcome, release_or_recover as recover


@dataclass(frozen=True)
class SourcePin:
    incident_id: str
    source_id: str
    revision: int


def release_or_recover(candidate, *, incident_id, records=(), pins=()):
    """Pins come from the trusted owner, never from candidate/retrieved text.

    Exact revisions are a freshness contract, not a clock or authentication.
    Every applicable record must pass; newer records do not override old ones.
    """
    def abstain(reason):
        return Outcome("abstained", None, True, (reason,), ())

    if type(incident_id) is not str or not incident_id:
        return abstain("invalid_incident")
    if type(records) is not tuple or type(pins) is not tuple:
        return abstain("invalid_trusted_input")
    if any(type(p) is not SourcePin or type(p.incident_id) is not str
           or not p.incident_id or type(p.source_id) is not str or not p.source_id
           or type(p.revision) is not int or p.revision < 1 for p in pins):
        return abstain("invalid_pin")
    if any(type(r) is not FactRecord or type(r.incident_id) is not str
           or not r.incident_id for r in records):
        return abstain("invalid_record")
    selected = tuple(r for r in records if r.incident_id == incident_id)
    if not selected:
        return abstain("missing_facts")
    applicable = tuple(p for p in pins if p.incident_id == incident_id)
    revisions = {}
    for p in applicable:
        revisions.setdefault(p.source_id, set()).add(p.revision)
    if any(len(values) != 1 for values in revisions.values()):
        return abstain("ambiguous_revision")
    for r in selected:
        if type(r.source_id) is not str or r.source_id not in revisions:
            return abstain("source_incident_mismatch")
        if type(r.revision) is not int or r.revision < 1:
            return abstain("invalid_revision")
        expected = next(iter(revisions[r.source_id]))
        if r.revision != expected:
            return abstain("stale_revision" if r.revision < expected else "unpinned_revision")
    return recover(candidate, incident_id=incident_id, records=selected,
                   approved_sources=tuple(revisions))
