"""Deterministic offline outbox recovery and lease fencing regressions."""
from contextlib import closing
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
from day26_lifecycle import Authority
from day30_outbox import Outbox
from tests import test_day27_release as fixtures


def race(path, barrier, output):
    fixture = fixtures.ReleaseQueueTests()
    fixture.setUp()
    box = Outbox(fixture.state, path)
    barrier.wait(10)
    output.put(box.claim('job:30', recipient='owner:alice', task=TASK, now=1001) is not None)


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'outbox.sqlite'
        Outbox.provision(self.path)
        fixture = fixtures.ReleaseQueueTests()
        fixture.setUp()
        self.state = fixture.state
        self.restart()

    def restart(self):
        self.box = Outbox(self.state, self.path)

    def enqueue(self, operation='job:30'):
        return self.box.enqueue(operation, self.box.prepare(), 'candidate-marker',
                                original=Decision(False, None, ('blocked',)), now=self.state.snapshot.now)

    def claim(self, **changes):
        args = dict(recipient='owner:alice', task=TASK, now=1001)
        args.update(changes)
        return self.box.claim('job:30', **args)

    def test_durable_intent_and_ack_without_network(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('offline only')):
            self.assertTrue(self.enqueue())
            self.restart()
            claim = self.claim()
            self.assertIn('23 minutes', claim.outcome.text)
            self.assertTrue(self.box.ack(claim, now=1002))
        self.restart()
        self.assertIsNone(self.claim(now=1007))
        self.assertTrue(self.enqueue())
        self.assertIsNone(self.claim(now=1007))
        self.assertNotIn(b'candidate-marker', self.path.read_bytes())

    def test_duplicate_enqueue_and_binding_cannot_replace_intent(self):
        self.assertTrue(self.enqueue())
        self.assertTrue(self.enqueue())
        self.state = replace(self.state, lease=replace(self.state.lease, lease_id='lease:other'))
        self.restart()
        self.assertFalse(self.enqueue())
        self.assertIsNone(self.claim())
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM outbox').fetchone(), (1,))

    def test_lease_expiry_ack_loss_and_receiver_deduplication(self):
        self.enqueue()
        first = self.claim()
        self.assertIsNone(self.claim(now=1005))
        self.restart()
        second = self.claim(now=1006)
        self.assertNotEqual(first.token, second.token)
        self.assertEqual(first.outcome.text, second.outcome.text)
        # A naive receiver applies twice; a keyed receiver applies once.
        naive_effects, keyed_effects, seen = [], [], set()
        def receive(claim):
            naive_effects.append(claim.outcome.text)
            if claim.operation_id not in seen:
                seen.add(claim.operation_id)
                keyed_effects.append(claim.outcome.text)
        receive(first)
        receive(second)
        self.assertEqual(naive_effects, [first.outcome.text] * 2)
        self.assertEqual(keyed_effects, [first.outcome.text])
        self.assertFalse(self.box.ack(first, now=1007))
        self.assertTrue(self.box.ack(second, now=1007))
        self.assertFalse(self.box.ack(second, now=1007))

    def test_retry_limit_and_clock_rollback(self):
        self.enqueue()
        first = self.claim(max_attempts=2)
        self.assertFalse(self.box.ack(first, now=1000))
        self.assertFalse(self.box.ack(first, now=1006))
        self.assertIsNotNone(self.claim(now=1006, max_attempts=2))
        self.assertIsNone(self.claim(now=1005, max_attempts=2))
        self.assertIsNone(self.claim(now=1011, max_attempts=2))

    def test_recipient_task_expiry_revocation_and_changed_context(self):
        self.enqueue()
        for changes in (dict(recipient='owner:bob'), dict(task='other'), dict(now=1040),
                        dict(now=999), dict(now=True)):
            with self.subTest(changes=changes):
                self.assertIsNone(self.claim(**changes))
        states = (replace(self.state, authority=Authority(5, ('lease:27',))),
                  replace(self.state, lease=replace(self.state.lease, lease_id='lease:new')),
                  replace(self.state, snapshot=replace(self.state.snapshot, authorized=False)))
        for state in states:
            with self.subTest(state=state):
                self.box.update(state)
                self.assertIsNone(self.claim())
        self.box.update(self.state)
        self.assertIsNotNone(self.claim())

    def test_fresh_clock_restart_and_stale_ticket(self):
        ticket = self.box.prepare()
        self.box.update(self.state)
        self.assertFalse(self.box.enqueue('stale', ticket, '', original=Decision(False, None, ()), now=1000))
        self.enqueue()
        self.state = replace(self.state, snapshot=replace(self.state.snapshot, now=1002))
        self.restart()
        self.assertIsNotNone(self.claim(now=1002))

    def test_two_processes_claim_one_lease(self):
        self.enqueue()
        ctx = multiprocessing.get_context('spawn')
        barrier, output = ctx.Barrier(2), ctx.Queue()
        processes = [ctx.Process(target=race, args=(str(self.path), barrier, output)) for _ in range(2)]
        try:
            for process in processes:
                process.start()
            results = [output.get(timeout=20) for _ in processes]
            for process in processes:
                process.join(20)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(sum(results), 1)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            output.close()

    def test_missing_corrupt_incompatible_storage_fails_closed(self):
        for kind in ('missing', 'corrupt', 'schema', 'version'):
            with self.subTest(kind=kind):
                if self.path.exists():
                    self.path.unlink()
                if kind == 'corrupt':
                    self.path.write_bytes(b'broken')
                elif kind in ('schema', 'version'):
                    Outbox.provision(self.path)
                    with closing(sqlite3.connect(self.path)) as db, db:
                        db.execute('DROP TABLE outbox' if kind == 'schema' else 'PRAGMA user_version=1')
                self.assertFalse(self.enqueue())
                self.assertIsNone(self.claim())
                if kind == 'missing':
                    self.assertFalse(self.path.exists())

    def test_storage_lock_blocks_enqueue_claim_and_ack(self):
        self.enqueue()
        claim = self.claim()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('BEGIN IMMEDIATE')
            self.assertFalse(self.enqueue('other'))
            self.assertIsNone(self.claim(now=1006))
            self.assertFalse(self.box.ack(claim, now=1002))

    def test_commit_uncertainty_never_returns_handoff(self):
        self.enqueue()
        connect = sqlite3.connect
        for committed in (False, True):
            with self.subTest(committed=committed):
                class Connection:
                    def __init__(self, *args, **kwargs):
                        self.db = connect(*args, **kwargs)
                    def execute(self, *args):
                        return self.db.execute(*args)
                    def commit(self):
                        if committed:
                            self.db.commit()
                        raise sqlite3.OperationalError('uncertain commit')
                    def rollback(self):
                        self.db.rollback()
                    def close(self):
                        self.db.close()
                with patch('day30_outbox.sqlite3.connect', side_effect=Connection):
                    self.assertIsNone(self.claim())
                self.restart()
                if committed:
                    self.assertIsNone(self.claim())
                    self.assertIsNotNone(self.claim(now=1006))
                else:
                    claim = self.claim()
                    self.assertIsNotNone(claim)
                    # Reset the lease for the next independent fault scenario.
                    with closing(connect(self.path)) as db, db:
                        db.execute("UPDATE outbox SET status='pending', attempts=0")

    def test_abrupt_process_exit_before_and_after_enqueue_commit(self):
        for committed in (False, True):
            with self.subTest(committed=committed):
                script = '''import os, sys
from day30_outbox import Outbox
from day21_gate import Decision
from tests import test_day27_release as fixtures
f = fixtures.ReleaseQueueTests(); f.setUp()
b = Outbox(f.state, sys.argv[1])
original = b._transaction
from contextlib import contextmanager
@contextmanager
def crash():
    with original() as db:
        yield db
        if sys.argv[2] == 'False': os._exit(30)
    os._exit(30)
b._transaction = crash
b.enqueue(sys.argv[2], b.prepare(), '', original=Decision(False, None, ('blocked',)), now=1000)
'''
                process = subprocess.run([sys.executable, '-B', '-S', '-c', script,
                                          str(self.path), str(committed)], check=False)
                self.assertEqual(process.returncode, 30)
                self.restart()
                result = self.box.claim(str(committed), recipient='owner:alice', task=TASK, now=1001)
                self.assertEqual(result is not None, committed)
                if not committed:
                    self.assertTrue(self.enqueue(str(committed)))

    def test_abrupt_exit_after_claim_recovers_when_lease_expires(self):
        self.enqueue()
        script = """import os, sys
from day30_outbox import Outbox
from day24_recovery import TASK
from tests import test_day27_release as fixtures
f = fixtures.ReleaseQueueTests(); f.setUp()
b = Outbox(f.state, sys.argv[1])
assert b.claim('job:30', recipient='owner:alice', task=TASK, now=1001)
os._exit(30)
"""
        process = subprocess.run([sys.executable, '-B', '-S', '-c', script, str(self.path)], check=False)
        self.assertEqual(process.returncode, 30)
        self.restart()
        self.assertIsNone(self.claim(now=1005))
        self.assertIsNotNone(self.claim(now=1006))

    def test_provision_and_malformed_inputs(self):
        with self.assertRaises(FileExistsError):
            Outbox.provision(self.path)
        for operation in ('', None, [], True, 'x' * 129):
            self.assertFalse(self.enqueue(operation))
        self.enqueue()
        for changes in (dict(lease_seconds=0), dict(lease_seconds=True), dict(max_attempts=0),
                        dict(max_attempts=11), dict(now=None)):
            self.assertIsNone(self.claim(**changes))
        self.assertFalse(self.box.ack(None, now=1001))
