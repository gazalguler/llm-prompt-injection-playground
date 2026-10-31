"""Regression checks for pinned provenance and conservative abstention."""
from dataclasses import replace
import itertools
import json
import socket
import unittest
from unittest.mock import patch

from day18_cases import EXPECTED, RECORDS
from day19_analysis import ROOT, analyze
from day19_cases import cases
from day19_recovery import SourcePin, release_or_recover


class Day19Tests(unittest.TestCase):
    def test_cases_and_record_order(self):
        for case in cases():
            for records in itertools.permutations(case["records"]):
                with self.subTest(case=case["case_id"], records=records):
                    result = release_or_recover(case["candidate"], incident_id=case["incident_id"],
                                                records=records, pins=case["pins"])
                    self.assertEqual(result.status, case["expected_status"])
                    self.assertEqual(result.text, case["expected_text"])
                    self.assertEqual(result.reasons, case["expected_reasons"])
                    self.assertEqual(result.provenance, case["expected_provenance"])

    def test_malformed_trusted_inputs(self):
        a = RECORDS[0]
        pin = SourcePin(a.incident_id, a.source_id, a.revision)
        variants = [dict(records=value) for value in (None, [], ({},), (replace(a, revision=True),),
                    (replace(a, incident_id=None),), (replace(a, duration_minutes=True),))]
        variants += [dict(pins=value) for value in (None, [], ({},), (replace(pin, revision=True),),
                     (replace(pin, source_id=""),), (replace(pin, incident_id=None),))]
        variants += [dict(incident_id=value) for value in (None, "", 1)]
        for override in variants:
            args = dict(incident_id=a.incident_id, records=(a,), pins=(pin,))
            args.update(override)
            with self.subTest(override=override):
                result = release_or_recover(EXPECTED[0], **args)
                self.assertEqual(result.status, "abstained")
                self.assertIsNone(result.text)
                self.assertEqual(result.provenance, ())

    def test_agreeing_sources_retain_provenance(self):
        a = RECORDS[0]
        b = replace(a, source_id="owner/independent", revision=4)
        pins = tuple(SourcePin(r.incident_id, r.source_id, r.revision) for r in (a, b))
        result = release_or_recover(None, incident_id=a.incident_id, records=(b, a), pins=pins)
        self.assertEqual(result.text, EXPECTED[0])
        self.assertEqual(result.provenance, tuple(sorted(((a.source_id, a.revision), (b.source_id, 4)))))

    def test_report_offline_and_saved(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            report = analyze()
        self.assertEqual(report["totals"], dict(cases=42, expectations_met=42, released=6,
                         recovered=6, abstentions=30, task_completed=12, unsupported_claims=0))
        self.assertEqual(report, json.loads((ROOT / "day19_replay.json").read_text(encoding="utf-8")))
