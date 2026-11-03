"""Offline development replay of all 16 published Qwen outputs; no model calls."""
import argparse
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from day21_gate import check_output

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "results/local-qwen-proposed-001"


def analyze():
    evidence = json.loads((PUBLIC / "evidence.json").read_text())
    with (PUBLIC / "cases.csv").open(newline="") as stream:
        cases = list(csv.DictReader(stream))
    if [c["trial_id"] for c in cases] != [e["trial_id"] for e in evidence]:
        raise ValueError("Evidence/review identity mismatch")
    rows = []
    for case, item in zip(cases, evidence):
        # Trusted experiment routing, never a task selected by model/tool text.
        task = case["case_id"] if case["kind"] == "control" else "incident"
        decision = check_output(item["response"]["message"]["content"], task_contract=task + ":v1")
        rows.append(dict(trial_id=case["trial_id"], kind=case["kind"], condition=case["condition"],
                         original_attack_success=case["attack_success"],
                         original_task_completed=case["task_completed"], **asdict(decision)))
    totals = []
    for condition in ("baseline", "trust_boundary"):
        group = [r for r in rows if r["condition"] == condition]
        attacks = [r for r in group if r["kind"] == "attack"]
        controls = [r for r in group if r["kind"] == "control"]
        totals.append(dict(condition=condition, attacks=len(attacks), controls=len(controls),
                           attacks_withheld=sum(not r["released"] for r in attacks),
                           reviewed_successes_released=sum(r["released"] and r["original_attack_success"] == "success" for r in attacks),
                           attacks_released=sum(r["released"] for r in attacks),
                           controls_released=sum(r["released"] for r in controls)))
    names = ["day21_gate.py", "day21_analysis.py", "results/local-qwen-proposed-001/evidence.json", "results/local-qwen-proposed-001/cases.csv"]
    return json.loads(json.dumps(dict(method="offline development replay; no new model resistance estimate", sources={n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names}, totals=totals, decisions=rows)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = analyze()
    if args.check:
        if result != json.loads((ROOT / "day21_replay.json").read_text()):
            raise SystemExit("Day 21 replay mismatch")
        print("Day 21 replay verified.")
    else:
        print(json.dumps(result, indent=2))
