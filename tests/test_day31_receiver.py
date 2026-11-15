"""Offline receiver transactions integrated with real Day 30 outbox claims."""
from contextlib import closing, contextmanager
from dataclasses import replace
import multiprocessing
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from day21_gate import Decision
from day24_recovery import TASK
from day30_outbox import Outbox
from day31_receiver import Receiver, dispatch
from tests import test_day27_release as fixtures


def race(path, claim, barrier, output):
    receiver = Receiver(path, recipient='owner:alice', task=TASK)
    barrier.wait(10)
    output.put(receiver.receive(claim, recipient='owner:alice', task=TASK))


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'receiver.sqlite'
        self.outpath = Path(self.temp.name) / 'outbox.sqlite'
        Receiver.provision(self.path)
        Outbox.provision(self.outpath)
        fixture = fixtures.ReleaseQueueTests()
        fixture.setUp()
        self.state = fixture.state
        self.box = Outbox(self.state, self.outpath)
        self.receiver = Receiver(self.path, recipient='owner:alice', task=TASK)
        self.assertTrue(self.box.enqueue('job:31', self.box.prepare(), 'discarded-candidate',
                        original=Decision(False, None, ('blocked',)), now=1000))
        self.claim = self.box.claim('job:31', recipient='owner:alice', task=TASK, now=1001)
        self.assertIsNotNone(self.claim)

    def receive(self, claim=None, **kwargs):
        args = dict(recipient='owner:alice', task=TASK)
        args.update(kwargs)
        return self.receiver.receive(self.claim if claim is None else claim, **args)

    def counts(self):
        with closing(sqlite3.connect(self.path)) as db:
            return tuple(db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                         for table in ('receipts', 'effects'))

    def test_duplicate_and_restart_without_network(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('offline only')):
            self.assertEqual(self.receive(), 'applied')
            self.receiver = Receiver(self.path, recipient='owner:alice', task=TASK)
            self.assertEqual(self.receive(), 'duplicate')
        self.assertEqual(self.counts(), (1, 1))
        self.assertNotIn(b'discarded-candidate', self.path.read_bytes())

    def test_lost_ack_retries_through_existing_outbox(self):
        self.assertEqual(self.receive(), 'applied')
        self.box = Outbox(self.state, self.outpath)
        self.assertFalse(dispatch(self.box, self.receiver, 'job:31', recipient='owner:alice', task=TASK, now=1005))
        self.assertTrue(dispatch(self.box, self.receiver, 'job:31', recipient='owner:alice', task=TASK, now=1006))
        self.assertFalse(self.box.ack(self.claim, now=1007))
        self.assertIsNone(self.box.claim('job:31', recipient='owner:alice', task=TASK, now=1011))
        self.assertEqual(self.counts(), (1, 1))

    def test_payload_recipient_task_binding(self):
        self.assertIsNone(self.receive(recipient='owner:bob'))
        self.assertIsNone(self.receive(task='other'))
        self.assertEqual(self.counts(), (0, 0))
        self.assertEqual(self.receive(), 'applied')
        altered = replace(self.claim, outcome=replace(self.claim.outcome, text=self.claim.outcome.text + ' altered'))
        self.assertIsNone(self.receive(altered))
        for recipient, task in (('owner:bob', TASK), ('owner:alice', 'other')):
            other = Receiver(self.path, recipient=recipient, task=task)
            self.assertIsNone(other.receive(self.claim, recipient=recipient, task=task))
        self.assertEqual(self.receive(replace(self.claim, token='new-token')), 'duplicate')
        self.assertEqual(self.counts(), (1, 1))

    def test_distinct_key_is_distinct_work(self):
        self.assertEqual(self.receive(), 'applied')
        self.assertEqual(self.receive(replace(self.claim, operation_id='another')), 'applied')
        self.assertEqual(self.counts(), (2, 2))

    def test_two_processes_apply_one_effect(self):
        ctx = multiprocessing.get_context('spawn')
        barrier, output = ctx.Barrier(2), ctx.Queue()
        processes = [ctx.Process(target=race, args=(str(self.path), self.claim, barrier, output)) for _ in range(2)]
        try:
            for process in processes:
                process.start()
            results = [output.get(timeout=20) for _ in processes]
            for process in processes:
                process.join(20)
                self.assertEqual(process.exitcode, 0)
            self.assertCountEqual(results, ['applied', 'duplicate'])
            self.assertEqual(self.counts(), (1, 1))
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            output.close()

    def test_effect_failure_rolls_back_key_and_prevents_ack(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER fail_effect BEFORE INSERT ON effects BEGIN SELECT RAISE(ABORT, 'fault'); END")
        self.assertFalse(dispatch(self.box, self.receiver, 'job:31', recipient='owner:alice', task=TASK, now=1006))
        self.assertEqual(self.counts(), (0, 0))
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DROP TRIGGER fail_effect')
        self.assertTrue(dispatch(self.box, self.receiver, 'job:31', recipient='owner:alice', task=TASK, now=1011))
        self.assertEqual(self.counts(), (1, 1))

    def test_missing_corrupt_schema_version_and_lock_fail_closed(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('BEGIN IMMEDIATE')
            self.assertIsNone(self.receive())
        self.assertEqual(self.counts(), (0, 0))
        for kind in ('missing', 'corrupt', 'schema', 'version'):
            with self.subTest(kind=kind):
                self.path.unlink(missing_ok=True)
                if kind == 'corrupt':
                    self.path.write_bytes(b'broken')
                elif kind in ('schema', 'version'):
                    Receiver.provision(self.path)
                    with closing(sqlite3.connect(self.path)) as db, db:
                        db.execute('DROP TABLE effects' if kind == 'schema' else 'PRAGMA user_version=1')
                self.assertIsNone(self.receive())
                if kind == 'missing':
                    self.assertFalse(self.path.exists())

    def test_commit_uncertainty_resolves_on_retry(self):
        original = self.receiver._transaction
        for committed in (False, True):
            with self.subTest(committed=committed):
                claim = replace(self.claim, operation_id=str(committed))
                @contextmanager
                def uncertain():
                    with original() as db:
                        yield db
                        if not committed:
                            raise sqlite3.OperationalError('before commit')
                    raise sqlite3.OperationalError('after commit')
                with patch.object(self.receiver, '_transaction', uncertain):
                    self.assertIsNone(self.receive(claim))
                self.assertEqual(self.receive(claim), 'duplicate' if committed else 'applied')
        self.assertEqual(self.counts(), (2, 2))

    def test_process_exit_before_and_after_receiver_commit(self):
        for committed in (False, True):
            with self.subTest(committed=committed):
                script = '''import os, sys
from contextlib import contextmanager
from day30_outbox import Outbox
from day31_receiver import Receiver
from day24_recovery import TASK
from tests import test_day27_release as fixtures
f = fixtures.ReleaseQueueTests(); f.setUp()
b = Outbox(f.state, sys.argv[1])
c = b.claim('job:31', recipient='owner:alice', task=TASK, now=int(sys.argv[3]))
assert c is not None
r = Receiver(sys.argv[2], recipient='owner:alice', task=TASK)
original = r._transaction
@contextmanager
def crash():
    with original() as db:
        yield db
        if sys.argv[4] == 'False': os._exit(31)
    os._exit(31)
r._transaction = crash
r.receive(c, recipient='owner:alice', task=TASK)
'''
                now = 1006 if not committed else 1011
                process = subprocess.run([sys.executable, '-B', '-S', '-c', script,
                                          str(self.outpath), str(self.path), str(now), str(committed)], check=False)
                self.assertEqual(process.returncode, 31)
                self.assertEqual(self.counts(), (1, 1) if committed else (0, 0))
        self.assertEqual(self.receive(), 'duplicate')
        self.assertEqual(self.counts(), (1, 1))

    def test_provision_and_invalid_inputs(self):
        with self.assertRaises(FileExistsError):
            Receiver.provision(self.path)
        self.assertIsNone(self.receiver.receive(None, recipient='owner:alice', task=TASK))
        for key in ('', 'x' * 129, None, True):
            self.assertIsNone(self.receive(replace(self.claim, operation_id=key)))
        self.assertIsNone(self.receive(replace(self.claim, outcome=replace(self.claim.outcome, released=False))))
        self.assertEqual(self.counts(), (0, 0))
