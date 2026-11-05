"""Day 23 preregistered local evaluation. Default and --check are strictly offline.

Execution requires explicit approval outside this program and the exact approved
plan digest. A fixed exclusive run reservation makes failures non-resumable.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import socket
from unittest.mock import patch

import ollama_evaluate as transport
from day21_live import validate_model, validate_response
from day21_gate import check_output as day21
from day22_gate import check_output as day22

REPO = Path(__file__).resolve().parent
PLAN = REPO / "day23_plan.json"
HASH = REPO / "day23_plan.sha256"
RUN = REPO / "day23_runs" / "local-qwen-day23-001"
SOURCES = ("day23_evaluate.py", "day21_gate.py", "day22_gate.py", "day21_live.py",
           "ollama_evaluate.py", "day11_attack_cases.py", "day11_messages.py",
           "day11_retrieval.py", "day14_trials.py", "day23_cases.json")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    transport.save_json(path, value)


def load_plan():
    raw = PLAN.read_bytes()
    digest = sha(raw)
    if HASH.read_text().strip() != digest:
        raise ValueError("Plan checksum mismatch")
    plan = json.loads(raw)
    if (plan["request_count"] != 8 or plan["maximum_inference_calls"] != 8
            or plan["retries"] != 0 or len(plan["requests"]) != 8):
        raise ValueError("Expected exactly eight requests, zero retries")
    if plan["sources"] != {n: sha((REPO / n).read_bytes()) for n in SOURCES}:
        raise ValueError("Frozen source mismatch; do not refit the gate")
    rows = plan["requests"]
    if len({r["trial_id"] for r in rows}) != 8:
        raise ValueError("Duplicate trial")
    for i in range(0, 8, 2):
        attack, control = rows[i:i+2]
        if (attack["kind"], control["kind"]) != ("attack", "control") or attack["facts"] != control["facts"]:
            raise ValueError("Pair identity mismatch")
        for row in (attack, control):
            if row["request_sha256"] != transport.fingerprint(row["request"]):
                raise ValueError("Request checksum mismatch")
            if (row["request"]["model"] != transport.MODEL or row["request"]["stream"] is not False
                    or row["request"]["options"] != dict(temperature=0, seed=23, num_predict=200, num_ctx=4096)):
                raise ValueError("Request bounds mismatch")
    return plan, digest


def decisions(text, row):
    # Facts and pins only come from the sealed caller plan, never retrieved text.
    return json.loads(json.dumps(dict(day21=asdict(day21(text, task_contract="incident:v1")),
                day22=asdict(day22(text, facts=row["facts"], task_id=row["task_id"], revision=row["revision"])))))


def offline():
    plan, digest = load_plan()
    cases = json.loads((REPO / "day23_cases.json").read_text())
    rows = []
    for case in cases:
        row = next(r for r in plan["requests"] if r["pair_id"] == case["pair_id"])
        result = decisions(case["text"], row)
        rows.append(dict(**case, decisions=result))
    return dict(method="authored offline probes, not model responses or held-out estimates",
                plan_sha256=digest, rows=rows,
                metrics={gate: dict(total=len(rows),
                    clean_correct=sum(r["clean_correct"] for r in rows),
                    clean_released=sum(r["clean_correct"] and r["decisions"][gate]["released"] for r in rows),
                    false_blocks=sum(r["clean_correct"] and not r["decisions"][gate]["released"] for r in rows),
                    invalid=sum(not r["clean_correct"] for r in rows),
                    invalid_blocked=sum(not r["clean_correct"] and not r["decisions"][gate]["released"] for r in rows))
                    for gate in ("day21", "day22")})


def run(approved_sha256):
    plan, digest = load_plan()
    if approved_sha256 != digest:
        raise ValueError("Execution requires the exact approved plan SHA-256")
    RUN.parent.mkdir(exist_ok=True)
    RUN.mkdir()  # Never resume, overwrite, or choose another ID after failure.
    attempts = completed = 0
    save(RUN / "plan.json", plan)
    with (RUN / "plan.sha256").open("x") as stream:
        stream.write(digest + "\n")
    (RUN / "sources").mkdir()
    for name in SOURCES:
        with (RUN / "sources" / name).open("xb") as stream:
            stream.write((REPO / name).read_bytes())
    try:
        for name in ("status", "tags", "version"):
            status, raw = transport.local_request("GET", "/api/" + name)
            with (RUN / (name + ".raw.json")).open("xb") as stream:
                stream.write(raw)
            save(RUN / (name + ".http.json"), dict(status=status))
            value = transport.decode(status, raw)
            if name == "status" and value.get("cloud", {}).get("disabled") is not True:
                raise ValueError("Cloud must be disabled")
            if name == "tags":
                validate_model(value)  # Exact frozen digest, installed local weights only.
        for index, row in enumerate(plan["requests"], 1):
            if attempts >= 8:
                raise ValueError("Budget exhausted")
            # Recheck frozen sources/plan before each call; no adaptive edits.
            if load_plan()[1] != digest:
                raise ValueError("Plan changed during run")
            prefix = RUN / f"response_{index:02d}"
            save(prefix.with_suffix(".attempt.json"), dict(attempt=index, trial_id=row["trial_id"],
                                                         request_sha256=row["request_sha256"]))
            attempts += 1  # Timeouts and malformed responses consume this attempt.
            status, raw = transport.local_request("POST", "/api/chat", row["request"])
            with prefix.with_suffix(".raw.json").open("xb") as stream:
                stream.write(raw)
            save(prefix.with_suffix(".http.json"), dict(status=status, trial_id=row["trial_id"]))
            text = validate_response(transport.decode(status, raw))
            save(prefix.with_suffix(".gate.json"), dict(trial_id=row["trial_id"], raw_sha256=sha(raw),
                                                        decisions=decisions(text, row)))
            completed += 1
        save(RUN / "complete.json", dict(attempted=attempts, completed=completed, retries=0))
    except Exception as error:
        save(RUN / "error.json", dict(error_type=type(error).__name__, message=str(error),
                                      attempted=attempts, completed=completed, retries=0))
        raise
    finally:
        save(RUN / "SHA256SUMS.json", {str(p.relative_to(RUN)): sha(p.read_bytes())
             for p in sorted(RUN.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.json"})
    return RUN


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--execute-local", metavar="APPROVED_PLAN_SHA256")
    args = parser.parse_args()
    if args.execute_local:
        print(run(args.execute_local))
    else:
        with patch.object(socket, "socket", side_effect=AssertionError("offline: network forbidden")):
            result = offline()
            if args.check:
                if result != json.loads((REPO / "day23_offline.json").read_text()):
                    raise SystemExit("Day 23 offline report mismatch")
                print("Day 23 plan, sources, decisions and offline metrics verified; no inference.")
            else:
                print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
