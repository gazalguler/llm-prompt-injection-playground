"""Deterministic recovery for the fixed incident contract; no model or retrieval."""
from dataclasses import dataclass

from day16_defense import check_summary


@dataclass(frozen=True)
class IncidentFacts:
    incident_id: str
    duration_minutes: int
    recovery: str


# Owner-defined fixture, reviewed against day15_cases.FACTS. Never populated
# from a candidate, tool result, or model assertion of verification.
TRUSTED_FACTS = IncidentFacts("synthetic-service-incident", 15, "database_restart")


@dataclass(frozen=True)
class Outcome:
    status: str
    text: str | None
    gate_reasons: tuple[str, ...]


def release_or_recover(candidate, *, incident_id, trusted_facts=None):
    decision = check_summary(candidate)
    if decision.released:
        return Outcome("released", decision.text, ())
    # Closed schema and exact contract: this renderer supports one incident only.
    # Caller must supply the owner-controlled record via a separate trusted path.
    valid = (type(trusted_facts) is IncidentFacts
             and type(trusted_facts.duration_minutes) is int
             and trusted_facts == TRUSTED_FACTS
             and incident_id == TRUSTED_FACTS.incident_id)
    if not valid:
        return Outcome("abstained", None, decision.reasons)
    text = (f"The application was unavailable for {trusted_facts.duration_minutes} minutes, "
            "and engineers restored service by restarting the database.")
    if not check_summary(text).released:
        return Outcome("abstained", None, decision.reasons + ("recovery_validation",))
    return Outcome("recovered", text, decision.reasons)
