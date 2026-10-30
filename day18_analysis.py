"""Deterministic multi-incident replay, without APIs or external packages."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from day17_analysis import source_digest
from day18_cases import SOURCES, cases
from day18_recovery import release_or_recover

ROOT = Path(__file__).resolve().parent


def analyze():
    rows = []
    for case in cases():
        result = release_or_recover(case["candidate"], incident_id=case["incident_id"],
                                    records=case["records"], approved_sources=SOURCES)
        rows.append(dict(case_id=case["case_id"], kind=case["kind"], **asdict(result),
                         task_completed=result.text is not None and result.text == case["expected_text"],
                         unsupported_claim=result.text is not None and result.text != case["expected_text"],
                         expectation_met=result.status == case["expected_status"] and result.text == case["expected_text"]))
    totals = dict(cases=len(rows), contained=sum(r["contained"] for r in rows),
                  recovered=sum(r["status"] == "recovered" for r in rows),
                  abstentions=sum(r["status"] == "abstained" for r in rows),
                  released=sum(r["status"] == "released" for r in rows),
                  task_completed=sum(r["task_completed"] for r in rows),
                  unsupported_claims=sum(r["unsupported_claim"] for r in rows),
                  expectations_met=sum(r["expectation_met"] for r in rows))
    report = dict(method="offline synthetic development fixtures; exact output contract",
                  provenance={name: source_digest(ROOT / name) for name in
                              ("day18_cases.py", "day18_recovery.py", "day18_analysis.py")},
                  totals=totals, decisions=rows)
    return json.loads(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.check:
        if json.loads((ROOT / "day18_replay.json").read_text(encoding="utf-8")) != report:
            raise SystemExit("Day 18 replay differs from saved report.")
        print("Day 18 replay verified.")
    else:
        print(json.dumps(report, indent=2))
