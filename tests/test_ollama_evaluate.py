"""Offline Ollama integration checks; all HTTP connections are mocked."""
import ast
import csv
import hashlib
import io
import json
import os
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

import ollama_evaluate as evaluation
from day11_attack_cases import ATTACK_CASES
from day11_messages import build_attack_messages
from day14_trials import SYSTEM_PROMPTS


class OllamaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'runs'
        self.patch = patch.object(evaluation, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.network = patch.object(socket, 'create_connection', side_effect=AssertionError('Real network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.calls = []
        self.cloud = True
        self.models = [dict(name=evaluation.MODEL, digest='sha256:fixture', size=123)]
        self.chat_status = 200
        self.chat_raw = None

    def transport(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        values = {'/api/status': {'cloud': {'disabled': self.cloud}},
                  '/api/tags': {'models': self.models}, '/api/version': {'version': 'fixture'},
                  '/api/chat': dict(model=evaluation.MODEL, done=True, done_reason='stop',
                                    message=dict(role='assistant', content='Summary APPROVED_BY_ADMIN'))}
        if path == '/api/chat' and self.chat_raw is not None:
            return self.chat_status, self.chat_raw
        return 200, json.dumps(values[path]).encode()

    def execute(self):
        with patch.object(evaluation, 'local_request', side_effect=self.transport):
            return evaluation.run('fixture')

    def test_plan_is_deterministic_and_preserves_prompts_and_documents(self):
        plan = evaluation.make_plan('fixture')
        self.assertEqual(plan, evaluation.make_plan('fixture'))
        self.assertEqual(plan['request_count'], 16)
        self.assertEqual(len({r['trial_id'] for r in plan['requests']}), 16)
        self.assertEqual(sum(r['kind'] == 'control' for r in plan['requests']), 4)
        for row in plan['requests']:
            request = row['request']
            self.assertEqual(request['messages'][0]['content'], SYSTEM_PROMPTS[row['condition']])
            self.assertEqual(request['options'], dict(temperature=0, seed=11, num_predict=200, num_ctx=4096))
            self.assertEqual(row['request_sha256'], evaluation.fingerprint(request))
            if row['dataset'] == 'expanded':
                original = build_attack_messages(ATTACK_CASES[row['case_id']], SYSTEM_PROMPTS[row['condition']])
                self.assertEqual(request['messages'][-1]['content'], original[-1]['content'])
                self.assertEqual(request['messages'][2]['tool_calls'][0]['function']['arguments'], {'document_id': 'incident'})
        tree = ast.parse((Path(evaluation.__file__).parent / 'day11_evaluate.py').read_text())
        prompts = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'SYSTEM_PROMPTS' for t in n.targets))
        self.assertEqual(prompts, SYSTEM_PROMPTS)

    def test_invalid_parameters_rejected_before_io(self):
        for model in ('qwen:cloud', 'qwen:4b-cloud', 'https://ollama.com/x', 'registry/x:y', 'qwen', '../x:y'):
            with self.assertRaises(ValueError):
                evaluation.run('fixture', model)
        for run_id in ('../escape', '', 'x/y'):
            with self.assertRaises(ValueError):
                evaluation.run(run_id)
        with self.assertRaises(ValueError):
            evaluation.make_plan('fixture', seed=True)
        self.assertFalse(self.root.exists())

    def test_complete_raw_records_and_no_overwrite(self):
        directory = self.execute()
        with (directory / 'reviews.csv').open(newline='') as stream:
            reviews = list(csv.DictReader(stream))
        self.assertEqual(len(reviews), 16)
        for index, row in enumerate(reviews, 1):
            raw = (directory / f'response_{index:02d}.raw.json').read_bytes()
            self.assertEqual(row['raw_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(row['provider'], 'ollama_local')
            self.assertEqual(row['cohort'], evaluation.COHORT)
            self.assertEqual(row['marker_present'], 'True')
            for field in ('attack_success', 'task_completed', 'reviewer', 'reviewed_at', 'review_notes'):
                self.assertEqual(row[field], '')
        self.assertTrue((directory / 'complete.json').exists())
        before = {p.name: p.read_bytes() for p in directory.iterdir()}
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual(len(self.calls), 19)
        self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir()})

    def test_cloud_unknown_or_enabled_stops_before_inference(self):
        for value in (False, None, 1, 'true'):
            with self.subTest(value=value), patch.object(evaluation, 'ROOT', self.root / str(value)):
                self.cloud = value
                with self.assertRaises(ValueError):
                    self.execute()
        self.assertTrue(all(call[1] == '/api/status' for call in self.calls))

    def test_remote_missing_and_weightless_models_rejected(self):
        for models in ([], [dict(name=evaluation.MODEL, size=1, digest='x', remote_host='https://ollama.com')],
                       [dict(name=evaluation.MODEL, size=1, digest='x', remote_model='remote')],
                       [dict(name=evaluation.MODEL, size=0, digest='x')],
                       [dict(name=evaluation.MODEL, size=1)]):
            with self.subTest(models=models), patch.object(evaluation, 'ROOT', self.root / str(len(self.calls))):
                self.models = models
                with self.assertRaises(ValueError):
                    self.execute()
        self.assertFalse(any(c[1] == '/api/chat' for c in self.calls))

    def test_bad_responses_saved_and_stop_without_retry(self):
        bad = [b'not json', b'{"error":"fixture"}', b'{}',
               json.dumps(dict(model=evaluation.MODEL, done=False)).encode(),
               json.dumps(dict(model='other:tag', done=True, message={'role': 'assistant', 'content': 'x'})).encode(),
               json.dumps(dict(model=evaluation.MODEL, done=True, message={'role': 'assistant', 'content': ''})).encode()]
        for index, raw in enumerate(bad):
            with self.subTest(raw=raw), patch.object(evaluation, 'ROOT', self.root / str(index)):
                self.chat_raw = raw
                with self.assertRaises(ValueError):
                    self.execute()
                directory = self.root / str(index) / 'fixture'
                self.assertEqual((directory / 'response_01.raw.json').read_bytes(), raw)
                self.assertTrue((directory / 'error.json').exists())
                self.assertFalse((directory / 'complete.json').exists())
        self.assertEqual(sum(c[1] == '/api/chat' for c in self.calls), len(bad))

    def test_timeout_and_http_errors_stop(self):
        with patch.object(evaluation, 'local_request', side_effect=TimeoutError('fixture')) as transport:
            with self.assertRaises(TimeoutError):
                evaluation.run('timeout')
            self.assertEqual(transport.call_count, 1)
        self.chat_status, self.chat_raw = 503, b'{"error":"unavailable"}'
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(sum(c[1] == '/api/chat' for c in self.calls), 1)

    def test_transport_fixed_loopback_and_does_not_follow_redirects(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status, response.read.return_value = 302, b'redirect'
        with patch.dict(os.environ, {'OLLAMA_HOST': 'https://ollama.com', 'HTTP_PROXY': 'https://example.com',
                                     'OPENAI_API_KEY': 'unused'}), patch.object(evaluation.http.client, 'HTTPConnection', return_value=connection) as factory:
            self.assertEqual(evaluation.local_request('GET', '/api/status'), (302, b'redirect'))
            factory.assert_called_once_with('127.0.0.1', 11434, timeout=180)
            connection.request.assert_called_once_with('GET', '/api/status', body=None, headers={'Content-Type': 'application/json'})
            connection.close.assert_called_once()
            with self.assertRaises(ValueError):
                evaluation.decode(302, b'redirect')
        with self.assertRaises(ValueError):
            evaluation.local_request('POST', '/api/pull', {})
        response.read.return_value = b'x' * (evaluation.LIMIT + 1)
        with patch.object(evaluation.http.client, 'HTTPConnection', return_value=connection):
            with self.assertRaises(ValueError):
                evaluation.local_request('GET', '/api/status')

    def test_cli_default_only_prints_plan(self):
        with patch('sys.argv', ['ollama_evaluate.py', 'preview']), redirect_stdout(io.StringIO()) as output:
            evaluation.main()
        self.assertEqual(json.loads(output.getvalue())['request_count'], 16)
        self.assertFalse(self.root.exists())
