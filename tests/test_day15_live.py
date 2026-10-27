"""Offline transport fixtures verify spending and failure boundaries."""
import contextlib
import io
import json
import socket
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from day15_live import execute, freeze, load_plan


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'run'
        self.quote = freeze(self.root, 'fixture')
        self.calls = 0

    def transport(self, request, key):
        self.calls += 1
        return 200, 'fixture-request', json.dumps(dict(model='gpt-4o-mini-2024-07-18',
            usage=dict(prompt_tokens=100, completion_tokens=20),
            choices=[dict(finish_reason='stop', message=dict(content='Synthetic fixture.'))])).encode()

    def run_fixture(self, transport=None, cap='0.10', plan_hash=None):
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')), contextlib.redirect_stdout(io.StringIO()):
            return execute(self.root, cap, plan_hash or self.quote['plan_sha256'],
                           'Offline fixture only', transport or self.transport)

    def test_complete_and_no_second_run(self):
        result = self.run_fixture()
        self.assertEqual((self.calls, result['completed'], result['status']), (72, 72, 'complete'))
        self.assertEqual(Decimal(result['reserved_usd']), Decimal(self.quote['conservative_usd']))
        self.assertEqual(len(list((self.root / 'responses').glob('*/raw.json'))), 72)
        with self.assertRaises(ValueError):
            self.run_fixture()
        other = Path(self.temp.name) / 'other'
        estimate = freeze(other, 'other')
        with self.assertRaises(FileExistsError):
            execute(other, '0.10', estimate['plan_sha256'], 'fixture', self.transport)
        self.assertEqual(self.calls, 72)

    def test_budget_hash_and_tampering_before_transport(self):
        for cap in ('0.001', 'NaN', 'Infinity', '-1'):
            with self.assertRaises(ValueError):
                self.run_fixture(cap=cap)
        with self.assertRaises(ValueError):
            self.run_fixture(plan_hash='bad')
        path = self.root / 'plan.json'
        plan = load_plan(self.root)
        plan['requests'][0]['request']['max_tokens'] = 201
        path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):
            self.run_fixture()
        self.assertEqual(self.calls, 0)

    def test_timeout_is_reserved_and_never_retried(self):
        def timeout(request, key):
            self.calls += 1
            raise TimeoutError('Do not disclose arbitrary error text')
        result = self.run_fixture(timeout)
        self.assertEqual((self.calls, result['attempted'], result['completed']), (1, 1, 0))
        self.assertTrue(result['unknown_charge_possible'])
        self.assertGreater(Decimal(result['reserved_usd']), 0)
        self.assertNotIn('disclose', (self.root / 'execution.jsonl').read_text())

    def test_http_error_raw_is_saved(self):
        result = self.run_fixture(lambda request, key: (429, 'fixture-id', b'{"error":"fixture"}'))
        self.assertEqual(result['attempted'], 1)
        self.assertEqual(result['completed'], 0)
        self.assertEqual((self.root / 'http_01.json').read_bytes(), b'{"error":"fixture"}')

    def test_unknown_usage_stops_after_saving_raw(self):
        result = self.run_fixture(lambda request, key: (200, 'fixture-id', b'{}'))
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['attempted'], 1)
        self.assertTrue((self.root / 'http_01.meta.json').exists())

    def test_existing_output_and_prepare_rejected(self):
        with self.assertRaises(FileExistsError):
            freeze(self.root, 'fixture')
        (self.root / 'http_01.json').write_bytes(b'old')
        with self.assertRaises(ValueError):
            self.run_fixture()
        self.assertEqual(self.calls, 0)
        self.assertEqual((self.root / 'http_01.json').read_bytes(), b'old')
