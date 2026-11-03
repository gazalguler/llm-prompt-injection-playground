"""Offline, closed-grammar fact gate. Caller facts/pins must be trusted.

This is compositional validation, not unrestricted English entailment. No repair,
retrieval, inference or automatic recovery. Every token must belong to a supported
factual sentence; extra instructions and alternate markers fail full parsing.
"""
import re
from day21_gate import Decision

DURATION = r"(?P<duration>[1-9][0-9]{0,3})"
COMPONENT = r"(?P<component>database|cache|worker)"
PATTERNS = (
    ("incident", rf"The (?:application|service) was unavailable for {DURATION} minutes, and engineers restored service by restarting the {COMPONENT}\."),
    ("incident", rf"The service incident report states that the application was unavailable for {DURATION} minutes, during which engineers restored service by restarting the {COMPONENT}\."),
    ("incident", rf"(?:A|An) {DURATION}-minute outage ended after (?:a|the) {COMPONENT} (?:restart|reboot)\."),
    ("incident", rf"Engineers restarted the {COMPONENT} to restore service after {DURATION} minutes of downtime\."),
    ("incident", r"A quarter-hour outage ended after a (?P<component>database|cache|worker) reboot\."),
    ("deployment", r"The deployment (?:completed successfully|was successfully completed) at (?P<time>[0-2][0-9]:[0-5][0-9])(?:, and no customer-facing issues were reported| without any (?:reported )?customer-facing issues)\."),
    ("meeting", r"The (?:security )?team (?:agreed|decided) to review access logs on (?P<day>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) and investigate (?P<count>two|[1-9][0-9]?) outdated accounts\."),
)


def valid_facts(facts, task_id, revision):
    if type(facts) is not dict or type(task_id) is not str or not task_id or type(revision) is not int or revision < 1:
        return False
    if facts.get("task_id") != task_id or type(facts.get("revision")) is not int or facts["revision"] != revision:
        return False
    kind = facts.get("kind")
    fields = {"incident": {"duration", "component"}, "deployment": {"time", "issues"}, "meeting": {"day", "count"}}
    if type(kind) is not str or kind not in fields or set(facts) != {"task_id", "revision", "kind"} | fields[kind]:
        return False
    if kind == "incident":
        return type(facts["duration"]) is int and 1 <= facts["duration"] <= 9999 and type(facts["component"]) is str and facts["component"] in {"database", "cache", "worker"}
    if kind == "deployment":
        return type(facts["time"]) is str and re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", facts["time"]) is not None and facts["issues"] is False
    return type(facts["day"]) is str and facts["day"] in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"} and type(facts["count"]) is int and 1 <= facts["count"] <= 99


def check_output(candidate, *, facts, task_id, revision):
    if not valid_facts(facts, task_id, revision):
        return Decision(False, None, ("invalid_or_unpinned_facts",))
    if type(candidate) is not str or not candidate.strip():
        return Decision(False, None, ("missing_text",))
    text = candidate.strip()
    for kind, pattern in PATTERNS:
        match = re.fullmatch(pattern, text)
        if kind != facts["kind"] or match is None:
            continue
        parsed = match.groupdict()
        if kind == "incident":
            parsed["duration"] = int(parsed.get("duration", 15))
        elif kind == "deployment":
            parsed["issues"] = False
        else:
            parsed["count"] = 2 if parsed["count"] == "two" else int(parsed["count"])
        if all(facts[key] == value for key, value in parsed.items()):
            return Decision(True, text, ())
        return Decision(False, None, ("fact_mismatch",))
    return Decision(False, None, ("outside_supported_grammar",))
