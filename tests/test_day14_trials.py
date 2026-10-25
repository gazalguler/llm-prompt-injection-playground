"""Synthetic responses test storage, never model resistance."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from day14_trials import make_plan, prepare, record, SYSTEM_PROMPTS
from day11_attack_cases import ATTACK_CASES


class TrialTests(unittest.TestCase):
    def test_reproducible_coverage(self):
        plan = make_plan("fixture")
        self.assertEqual(plan, make_plan("fixture"))
        self.assertEqual(len({r['trial_id'] for r in plan['requests']}), 30)
        for case in ATTACK_CASES:
            for condition in SYSTEM_PROMPTS:
                self.assertEqual(sum(r['case_id'] == case and r['condition'] == condition
                                     for r in plan['requests']), 3)

    def test_boundaries_and_budget(self):
        plan = make_plan("expanded", expanded=True, max_requests=48)
        self.assertEqual(plan['request_count'], 48)
        self.assertEqual(plan['max_output_tokens'], 9600)
        for row in plan['requests']:
            messages = row['request']['messages']
            self.assertEqual(messages[0]['content'], SYSTEM_PROMPTS[row['condition']])
            if row['cohort'] == 'day11_repeat':
                self.assertEqual(json.loads(messages[-1]['content']), ATTACK_CASES[row['case_id']])
        for kwargs in ({'trials': 0}, {'trials': 11}, {'max_requests': 29}, {'expanded': True}):
            with self.assertRaises(ValueError):
                make_plan('invalid', **kwargs)
        with self.assertRaises(ValueError):
            make_plan('../escape')

    def test_offline_storage_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp, patch('socket.socket', side_effect=AssertionError('network')):
            directory = Path(temp) / 'run'
            plan = make_plan('fixture')
            prepare(directory, plan)
            with self.assertRaises(FileExistsError):
                prepare(directory, plan)
            raw = Path(temp) / 'synthetic.json'
            content = b'{"choices":[{"message":{"content":"APPROVED_BY_ADMIN"}}]}'
            raw.write_bytes(content)
            trial = plan['requests'][0]['trial_id']
            record(directory, trial, raw)
            with self.assertRaises(FileExistsError):
                record(directory, trial, raw)
            with self.assertRaises(ValueError):
                record(directory, 'unknown', raw)
            saved = next((directory / 'responses').glob('*/raw.json'))
            self.assertEqual(saved.read_bytes(), content)
            with saved.with_name('review.csv').open(newline='', encoding='utf-8') as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row['attack_success'], '')
            self.assertEqual(row['task_completed'], '')
            self.assertEqual(row['marker_present'], 'True')
