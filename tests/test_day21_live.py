"""Bounded live executor tests; sockets forbidden and all HTTP mocked."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import day21_live as live
from day21_gate import CONTRACTS


class Day21LiveTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'runs'
        self.calls = []
        self.cloud = True
        self.models = [dict(name=live.ollama.MODEL, digest=live.DIGEST, size=123)]
        self.raw = None
        self.status = 200
        for target, attr, value in ((live, 'ROOT', self.root), (live, 'historical_hashes', lambda: {'fixture': 'unchanged'}),
                                    (socket, 'socket', unittest.mock.Mock(side_effect=AssertionError('network forbidden')))):
            item = patch.object(target, attr, value)
            item.start()
            self.addCleanup(item.stop)

    def transport(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path == '/api/chat' and self.raw is not None:
            if isinstance(self.raw, Exception):
                raise self.raw
            return self.status, self.raw
        values = {'/api/status': {'cloud': {'disabled': self.cloud}},
                  '/api/tags': {'models': self.models}, '/api/version': {'version': 'fixture'},
                  '/api/chat': dict(model=live.ollama.MODEL, done=True, done_reason='stop',
                                    message=dict(role='assistant', content=CONTRACTS['incident:v1'][0]))}
        return 200, json.dumps(values[path]).encode()

    def execute(self):
        with patch.object(live.ollama, 'local_request', side_effect=self.transport), redirect_stdout(io.StringIO()):
            return live.run()

    def test_exact_eight_plan_and_one_run_only(self):
        plan = live.make_plan()
        self.assertEqual(len(plan['requests']), 8)
        self.assertEqual(sum(r['kind'] == 'attack' for r in plan['requests']), 6)
        self.assertTrue(all(r['condition'] == 'trust_boundary' for r in plan['requests']))
        directory = self.execute()
        self.assertEqual(sum(c[1] == '/api/chat' for c in self.calls), 8)
        self.assertEqual(len(self.calls), 11)
        self.assertEqual(json.loads((directory / 'complete.json').read_text())['completed'], 8)
        self.assertEqual(len(list(directory.glob('*.gate.json'))), 8)
        before = list(self.calls)
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual(self.calls, before)

    def test_preflight_stops_without_inference(self):
        for i, cloud in enumerate((False, None, 'true', 1)):
            self.cloud = cloud
            with patch.object(live, 'ROOT', self.root / str(i)):
                (self.root / str(i)).parent.mkdir(exist_ok=True)
                with self.assertRaises(ValueError):
                    self.execute()
        self.assertFalse(any(c[1] == '/api/chat' for c in self.calls))

    def test_model_digest_and_local_weight_validation(self):
        for models in ([], [dict(name=live.ollama.MODEL, digest='wrong', size=1)],
                       [dict(name=live.ollama.MODEL, digest=live.DIGEST, size=0)],
                       [dict(name=live.ollama.MODEL, digest=live.DIGEST, size=1, remote_host='remote')],
                       [dict(name=live.ollama.MODEL, digest=live.DIGEST, size=1, remote_model='remote')],
                       self.models * 2):
            self.models = models
            self.root.mkdir(exist_ok=True)
            with patch.object(live, 'ROOT', self.root / str(len(self.calls))):
                with self.assertRaises(ValueError):
                    self.execute()
        self.assertFalse(any(c[1] == '/api/chat' for c in self.calls))

    def test_failure_never_retries_and_preserves_attempt(self):
        for i, raw in enumerate((b'not json', b'{}', TimeoutError('fixture'),
                                json.dumps(dict(model=live.ollama.MODEL, done=True, done_reason='length',
                                           message=dict(role='assistant', content='incomplete'))).encode())):
            self.raw = raw
            self.root.mkdir(exist_ok=True)
            with patch.object(live, 'ROOT', self.root / str(i)):
                with self.assertRaises((ValueError, TimeoutError)):
                    self.execute()
                directory = live.ROOT / live.RUN_ID
                error = json.loads((directory / 'error.json').read_text())
                self.assertEqual(error['attempted'], 1)
                self.assertEqual(error['completed'], 0)
                self.assertTrue((directory / 'response_01.attempt.json').exists())
                self.assertFalse((directory / 'complete.json').exists())
                if isinstance(raw, bytes):
                    self.assertEqual((directory / 'response_01.raw.json').read_bytes(), raw)
        self.assertEqual(sum(c[1] == '/api/chat' for c in self.calls), 4)

    def test_sealed_evidence_verification_and_tamper_detection(self):
        directory = self.execute()
        reviews = []
        for i, trial in enumerate(live.make_plan()['requests'], 1):
            attack = trial['kind'] == 'attack'
            reviews.append(dict(trial_id=trial['trial_id'], raw_sha256=live.sha(directory / f'response_{i:02d}.raw.json'),
                                task_completed=attack, answer_contamination=False,
                                attack_success='resisted' if attack else 'not_applicable',
                                false_block=False, reviewer='test fixture', notes='synthetic mocked review'))
        live.save(directory / 'reviews.json', reviews)
        live.save(directory / 'report.json', live.summarize(directory))
        live.seal(directory)
        with redirect_stdout(io.StringIO()):
            live.verify(directory)
        (directory / 'response_01.raw.json').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            live.verify(directory)
        with self.assertRaises(FileExistsError):
            live.seal(directory)
