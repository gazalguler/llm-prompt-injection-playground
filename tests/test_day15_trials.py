"""Synthetic fixtures verify the evaluation plumbing, not model behavior."""
import csv
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from day10_cases import DAY10_CASES
from day11_attack_cases import ATTACK_CASES
from day14_trials import VARIANTS, SYSTEM_PROMPTS, prepare, record
from day15_cases import cases, FACTS
from day15_trials import make_plan, review_template, summarize, FIELDS


class Day15Tests(unittest.TestCase):
    def test_pairs_and_local_novelty(self):
        dataset = cases()
        self.assertEqual(len(dataset), 12)
        self.assertEqual(len({r['document']['content'] for r in dataset}), 12)
        old = [r['document'] for r in DAY10_CASES]
        old += [r['content'] for r in ATTACK_CASES.values()] + list(VARIANTS.values())
        for row in dataset:
            self.assertTrue(row['document']['content'].startswith(FACTS))
            self.assertNotIn(row['document']['content'], old)
            self.assertEqual(bool(row['objective']), row['kind'] == 'attack')
        for family in {r['pair_id'] for r in dataset}:
            self.assertEqual({r['kind'] for r in dataset if r['pair_id'] == family},
                             {'attack', 'control'})

    def test_plan_coverage_and_tool_isolation(self):
        plan = make_plan('test')
        self.assertEqual(plan, make_plan('test'))
        self.assertNotEqual(plan['requests'], make_plan('test', seed=16)['requests'])
        self.assertEqual(plan['request_count'], 72)
        self.assertEqual(plan['max_output_tokens'], 14400)
        self.assertEqual(len({r['trial_id'] for r in plan['requests']}), 72)
        for case in cases():
            for condition in SYSTEM_PROMPTS:
                rows = [r for r in plan['requests'] if r['case_id'] == case['case_id']
                        and r['condition'] == condition]
                self.assertEqual({r['repetition'] for r in rows}, {1, 2, 3})
                for row in rows:
                    messages = row['request']['messages']
                    self.assertEqual(messages[0]['content'], SYSTEM_PROMPTS[condition])
                    self.assertEqual(json.loads(messages[-1]['content']), case['document'])
                    self.assertEqual(messages[-1]['role'], 'tool')
                    self.assertEqual(messages[-1]['tool_call_id'],
                                     messages[-2]['tool_calls'][0]['id'])
        for kwargs in ({'trials': 0}, {'trials': True}, {'max_requests': 71}):
            with self.assertRaises(ValueError):
                make_plan('test', **kwargs)
        with self.assertRaises(ValueError):
            make_plan('../escape')

    def test_missing_reviews_and_integrity_offline(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(
                socket, 'socket', side_effect=AssertionError('network forbidden')):
            root = Path(temp) / 'run'
            plan = make_plan('fixture', trials=1)
            prepare(root, plan)
            review_template(root)
            self.assertEqual(sum(g['missing_response'] for g in summarize(root)), 24)
            self.assertEqual(sum(g['reviewed'] for g in summarize(root)), 0)
            with self.assertRaises(FileExistsError):
                review_template(root)
            trial = next(r for r in plan['requests'] if r['kind'] == 'control')
            raw = Path(temp) / 'synthetic.json'
            raw.write_text(json.dumps({'choices': [{'message': {'content': FACTS}}]}),
                           encoding='utf-8')
            record(root, trial['trial_id'], raw)
            with (root / 'reviews.csv').open(newline='', encoding='utf-8') as stream:
                reviews = list(csv.DictReader(stream))
            row = next(r for r in reviews if r['trial_id'] == trial['trial_id'])
            row.update(attack_success='not_applicable', task_completed='yes',
                       reviewer='synthetic fixture', reviewed_at='2026-10-26',
                       review_notes='Fixture only; both facts present.')

            def save():
                with (root / 'reviews.csv').open('w', newline='', encoding='utf-8') as stream:
                    writer = csv.DictWriter(stream, fieldnames=FIELDS)
                    writer.writeheader()
                    writer.writerows(reviews)

            save()
            groups = summarize(root)
            self.assertEqual(sum(g['reviewed'] for g in groups), 1)
            self.assertEqual(sum(g['outcomes']['not_applicable'] for g in groups), 1)
            row['attack_success'] = 'resisted'
            save()
            with self.assertRaises(ValueError):
                summarize(root)
            row['attack_success'] = 'not_applicable'
            save()
            next((root / 'responses').glob('*/raw.json')).write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                summarize(root)
