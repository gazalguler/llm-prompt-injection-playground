"""Offline checks for paid-run boundaries; synthetic responses only."""
import json
from pathlib import Path
import tempfile
import unittest
from day14_live import execute


class LiveBoundaries(unittest.TestCase):
    def run_fixture(self, mode):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            calls = []
            def fake(request, key):
                calls.append(request)
                raw = {'model': 'gpt-4o-mini-2024-07-18',
                    'usage': {'prompt_tokens': 250, 'completion_tokens': 20},
                    'choices': [{'message': {'content': 'Synthetic fixture.'}}]}
                if mode == 'missing_usage':
                    raw.pop('usage')
                if mode == 'oversized':
                    raw['usage']['prompt_tokens'] = 999999
                return (429 if mode == 'http_error' else 200), 'fixture', json.dumps(raw).encode()
            result = execute(root, 'fixture', fake)
            expected = 30 if mode == 'ok' else 1
            self.assertEqual(len(calls), expected)
            self.assertEqual(result['completed'], 30 if mode == 'ok' else 0)
            self.assertEqual(len(list((root/'day14_runs'/'fixture').glob('http_*.json'))), expected * 2)
            with self.assertRaises(FileExistsError):
                execute(root, 'second_run', fake)
            self.assertEqual(len(calls), expected)

    def test_exactly_thirty_and_no_second_run(self):
        self.run_fixture('ok')

    def test_errors_stop_without_retry(self):
        for mode in ('missing_usage', 'oversized', 'http_error'):
            with self.subTest(mode=mode):
                self.run_fixture(mode)
