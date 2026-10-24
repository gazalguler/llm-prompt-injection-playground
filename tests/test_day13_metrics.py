"""Metric semantics and reproducibility against the saved review fixtures."""
import copy
import tempfile
import unittest
from pathlib import Path

from day13_metrics import build_report, display, load_reviews, outputs, render_html, summarize

ROOT = Path(__file__).resolve().parents[1]


def record(case, outcome, task="yes"):
    return {"cohort": "fixture", "case_id": case, "condition": "baseline",
            "model": "fixture", "outcome": outcome, "task_completed": task}


class MetricsTests(unittest.TestCase):
    def test_controls_and_task_completion_are_separate(self):
        rows = [record("a", "success"), record("b", "partial", "no"),
                record("c", "resisted"), record("d", "not_applicable")]
        group = summarize(rows)[0]
        self.assertEqual(group["attack_success"], {"numerator": 1, "denominator": 3, "rate": 1 / 3})
        self.assertEqual(group["attack_task_completion"]["numerator"], 2)
        self.assertEqual(group["resisted_and_completed"]["numerator"], 1)
        self.assertEqual(group["control_task_completion"]["denominator"], 1)

    def test_empty_and_control_only_groups(self):
        self.assertEqual(summarize([]), [])
        group = summarize([record("control", "not_applicable")])[0]
        self.assertIsNone(group["attack_success"]["rate"])
        self.assertEqual(display(group["attack_success"]), "n/a (0 eligible)")

    def test_groups_do_not_pool_models_conditions_or_cohorts(self):
        rows = [record("a", "success")]
        for field, value in (("model", "other"), ("condition", "trust_boundary"), ("cohort", "other")):
            row = record("a", "resisted")
            row[field] = value
            rows.append(row)
        self.assertEqual(len(summarize(rows)), 4)

    def test_invalid_and_duplicate_reviews_fail(self):
        for rows in ([record("a", "success")] * 2, [record("a", "unknown")],
                     [record("a", "resisted", "")],
                     [dict(record("a", "success"), condition="typo")]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                summarize(rows)

    def test_historical_counts_and_denominators(self):
        report = build_report(ROOT)
        self.assertEqual(len(report["records"]), 32)
        expected = {
            ("day10_documents", "baseline"): (8, 0, 4, 3, 1, 2),
            ("day10_documents", "trust_boundary"): (8, 0, 0, 1, 7, 7),
            ("day11_initial", "baseline"): (1, 2, 0, 0, 1, 1),
            ("day11_initial", "trust_boundary"): (1, 2, 0, 0, 1, 1),
            ("day11_expanded", "baseline"): (5, 0, 2, 0, 3, 4),
            ("day11_expanded", "trust_boundary"): (5, 0, 0, 0, 5, 5),
        }
        actual = {}
        for g in report["groups"]:
            actual[g["cohort"], g["condition"]] = (
                g["attacks"], g["controls"], *g["outcomes"].values(),
                g["attack_task_completion"]["numerator"],
            )
        self.assertEqual(actual, expected)
        self.assertTrue(any(r["outcome"] == "partial" and not r["marker_present"] for r in report["records"]))
        self.assertTrue(any(r["outcome"] == "success" and r["task_completed"] == "yes" for r in report["records"]))

    def test_raw_changes_missing_reviews_and_mislabeled_controls_fail(self):
        from day13_metrics import SOURCES
        for mutation in ("response", "missing", "control", "duplicate", "marker"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for reviewed, _, raw in SOURCES.values():
                    for name in (reviewed, raw):
                        (root / name).write_bytes((ROOT / name).read_bytes())
                path = root / "day11_results_reviewed.csv"
                import csv
                with path.open(encoding="utf-8-sig", newline="") as stream:
                    reader = csv.DictReader(stream)
                    fields, rows = reader.fieldnames, list(reader)
                if mutation == "response":
                    rows[0]["response"] = "changed"
                elif mutation == "missing":
                    rows.pop()
                elif mutation == "control":
                    rows[2]["attack_success"] = "resisted"
                elif mutation == "duplicate":
                    rows.append(rows[0])
                else:
                    rows[0]["marker_present"] = "True"
                with path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                with self.assertRaises(ValueError):
                    load_reviews(root)

    def test_report_is_deterministic_and_does_not_modify_sources(self):
        before = {p.name: p.read_bytes() for p in ROOT.glob("day1*_results*") if p.is_file()}
        self.assertEqual(outputs(ROOT), outputs(ROOT))
        for name, content in outputs(ROOT).items():
            self.assertEqual((ROOT / name).read_bytes(), content.encode("utf-8"))
        self.assertEqual(before, {p.name: p.read_bytes() for p in ROOT.glob("day1*_results*") if p.is_file()})

    def test_untrusted_response_is_escaped(self):
        report = copy.deepcopy(build_report(ROOT))
        report["records"][0]["response"] = '<script>alert("injection")</script>'
        rendered = render_html(report)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("https://", rendered)


if __name__ == "__main__":
    unittest.main()
