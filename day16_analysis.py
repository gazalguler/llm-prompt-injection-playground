"""Replay preserved responses through a release gate without model execution."""
import csv
import argparse
import hashlib
import json
from pathlib import Path

from day15_trials import summarize
from day16_defense import check_summary

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "day15_runs/live_20261026_001"


def analyze():
    summarize(RUN)  # Verify original requests, raw bytes and review associations.
    plan = json.loads((RUN / "plan.json").read_text(encoding="utf-8"))
    with (RUN / "reviews.csv").open(newline="", encoding="utf-8") as stream:
        reviews = {r["trial_id"]: r for r in csv.DictReader(stream)}
    recorded = {}
    for path in (RUN / "responses").glob("*/review.csv"):
        with path.open(newline="", encoding="utf-8") as stream:
            row = next(csv.DictReader(stream))
        recorded[row["trial_id"]] = (row, path.with_name("raw.json"))
    rows = []
    failures = []
    for trial in plan["requests"]:
        review = reviews[trial["trial_id"]]
        saved, raw = recorded[trial["trial_id"]]
        decision = check_summary(saved["response"])
        rows.append(dict(trial_id=trial["trial_id"], kind=trial["kind"],
                         condition=trial["condition"],
                         original_attack_success=review["attack_success"],
                         original_task_completed=review["task_completed"],
                         released=decision.released, reasons=decision.reasons))
        if trial["condition"] == "trust_boundary" and review["attack_success"] == "success":
            failures.append(dict(trial_id=trial["trial_id"], response=saved["response"],
                                 request_sha256=trial["request_sha256"],
                                 raw_path=raw.relative_to(ROOT).as_posix(),
                                 raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest()))
    totals = []
    for condition in ("baseline", "trust_boundary"):
        for kind in ("attack", "control"):
            group = [r for r in rows if r["condition"] == condition and r["kind"] == kind]
            totals.append(dict(condition=condition, kind=kind, count=len(group),
                               original_success=sum(r["original_attack_success"] == "success" for r in group),
                               original_partial=sum(r["original_attack_success"] == "partial" for r in group),
                               original_task=sum(r["original_task_completed"] == "yes" for r in group),
                               withheld=sum(not r["released"] for r in group),
                               released_success=sum(r["released"] and r["original_attack_success"] == "success" for r in group),
                               released_task=sum(r["released"] and r["original_task_completed"] == "yes" for r in group)))
    earlier = []
    for filename in ("day11_attacks_reviewed.csv", "day14_reviews.csv"):
        with (ROOT / filename).open(newline="", encoding="utf-8") as stream:
            historical = list(csv.DictReader(stream))
        for condition in ("baseline", "trust_boundary"):
            group = [r for r in historical if r["condition"] == condition]
            released = [r for r in group if check_summary(r["response"]).released]
            earlier.append(dict(source=filename, condition=condition, count=len(group),
                                source_sha256=hashlib.sha256((ROOT / filename).read_bytes()).hexdigest(),
                                original_task=sum(r["task_completed"] == "yes" for r in group),
                                released_task=sum(r["task_completed"] == "yes" for r in released),
                                withheld=len(group) - len(released),
                                released_success=sum(r["attack_success"] in {"success", "partial"} for r in released)))
    return dict(method="offline replay; no new model responses; original agent labels",
                failures=failures, totals=totals, earlier=earlier, decisions=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = json.dumps(analyze(), indent=2)
    if args.check:
        saved = json.loads((ROOT / "day16_replay.json").read_text(encoding="utf-8-sig"))
        if saved != json.loads(result):
            raise SystemExit("Day 16 replay differs from the saved report.")
        print("Day 16 replay verified.")
    else:
        print(result)
