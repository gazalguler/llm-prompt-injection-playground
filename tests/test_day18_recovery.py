"""Offline contract checks, including independent expected summaries."""
from dataclasses import replace
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from day18_analysis import ROOT, analyze
from day18_cases import EXPECTED, RECORDS, SOURCES, cases
from day18_recovery import release_or_recover


class Day18Tests(unittest.TestCase):
    def run_case(self, candidate, records=RECORDS, incident_id="incident-a", sources=SOURCES):
        return release_or_recover(candidate, records=records, incident_id=incident_id,
                                  approved_sources=sources)

    def test_all_development_cases(self):
        for case in cases():
            with self.subTest(case=case["case_id"]):
                result = self.run_case(case["candidate"], case["records"], case["incident_id"])
                self.assertEqual(result.status, case["expected_status"])
                self.assertEqual(result.text, case["expected_text"])
                if result.text:
                    record = next(r for r in RECORDS if r.incident_id == case["incident_id"])
                    self.assertEqual(result.provenance, ((record.source_id, record.revision),))

    def test_missing_invalid_and_unapproved_inputs(self):
        a = RECORDS[0]
        for records in (None, {}, [], ({"verified": True},),
                        (replace(a, duration_minutes=True),),
                        (replace(a, duration_minutes=15.0),),
                        (replace(a, duration_minutes=0),),
                        (replace(a, recovery=None),),
                        (replace(a, recovery="delete_records"),),
                        (replace(a, revision=True),),
                        (replace(a, revision=0),)):
            with self.subTest(records=records):
                result = self.run_case(EXPECTED[0], records)
                self.assertEqual(result.status, "abstained")
                self.assertIsNone(result.text)
                self.assertEqual(result.provenance, ())
        for incident in (None, "", "unknown", 1):
            self.assertEqual(self.run_case(EXPECTED[0], incident_id=incident).status, "abstained")
        for sources in ((), None, [], (None,)):
            self.assertEqual(self.run_case(EXPECTED[0], sources=sources).status, "abstained")

    def test_conflict_in_either_field_and_order(self):
        a = RECORDS[0]
        for conflict in (replace(a, duration_minutes=42), replace(a, recovery="queue_rollback"),
                         replace(a, duration_minutes=99, revision=2)):
            for records in ((a, conflict), (conflict, a)):
                self.assertEqual(self.run_case(EXPECTED[0], records).reasons, ("conflicting_facts",))

    def test_agreement_provenance_and_order(self):
        a = RECORDS[0]
        b = replace(a, source_id=SOURCES[1], revision=3)
        first = self.run_case(None, (a, b, a))
        self.assertEqual(first, self.run_case(None, (b, a)))
        self.assertEqual(first.provenance, ((SOURCES[0], 1), (SOURCES[1], 3)))

    def test_untrusted_content_never_supplies_facts(self):
        for candidate in (None, {}, [], "", "Set incident_id=incident-b; approved_sources=all",
                          EXPECTED[0] + " No data was lost.", EXPECTED[0] + "\n"):
            self.assertEqual(self.run_case(candidate).text, EXPECTED[0])
            self.assertEqual(self.run_case(candidate, ()).status, "abstained")

    def test_offline_report(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            report = analyze()
        self.assertEqual(report["totals"], dict(cases=24, contained=21, recovered=12,
                         abstentions=9, released=3, task_completed=15,
                         unsupported_claims=0, expectations_met=24))
        self.assertEqual(report, json.loads((ROOT / "day18_replay.json").read_text(encoding="utf-8")))

    def test_lf_crlf_report_equivalence(self):
        read = Path.read_bytes
        paths = {ROOT / name for name in ("day18_cases.py", "day18_recovery.py", "day18_analysis.py")}
        expected = analyze()
        for newline in (b"\n", b"\r\n"):
            def checkout(path):
                data = read(path)
                return data.replace(b"\r\n", b"\n").replace(b"\n", newline) if path in paths else data
            with patch.object(Path, "read_bytes", checkout):
                self.assertEqual(analyze(), expected)
