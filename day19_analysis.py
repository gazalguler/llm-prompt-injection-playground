"""Reproducible Day 19 replay; no network or model dependency."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from day17_analysis import source_digest
from day19_cases import cases
from day19_recovery import release_or_recover

ROOT = Path(__file__).resolve().parent


def analyze():
    rows = []
    for case in cases():
        result = release_or_recover(case["candidate"], incident_id=case["incident_id"],
                                    records=case["records"], pins=case["pins"])
        matches = (result.status == case["expected_status"] and result.text == case["expected_text"]
                   and result.reasons == case["expected_reasons"]
                   and result.provenance == case["expected_provenance"])
        rows.append(dict(case_id=case["case_id"], **asdict(result), expectation_met=matches,
                         task_completed=result.text is not None and result.text == case["expected_text"],
                         unsupported_claim=result.text is not None and result.text != case["expected_text"]))
    report = dict(method="offline synthetic development fixtures; owner-pinned revisions",
                  provenance={name: source_digest(ROOT / name) for name in
                              ("day19_recovery.py", "day19_cases.py", "day19_analysis.py",
                               "day18_recovery.py", "day18_cases.py")},
                  totals=dict(cases=len(rows), expectations_met=sum(r["expectation_met"] for r in rows),
                              released=sum(r["status"] == "released" for r in rows),
                              recovered=sum(r["status"] == "recovered" for r in rows),
                              abstentions=sum(r["status"] == "abstained" for r in rows),
                              task_completed=sum(r["task_completed"] for r in rows),
                              unsupported_claims=sum(r["unsupported_claim"] for r in rows)), decisions=rows)
    return json.loads(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.check:
        if report != json.loads((ROOT / "day19_replay.json").read_text(encoding="utf-8")):
            raise SystemExit("Day 19 replay differs from saved report.")
        print("Day 19 replay verified.")
    else:
        print(json.dumps(report, indent=2))
