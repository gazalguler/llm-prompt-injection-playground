"""Offline restart, process race and abrupt-exit regressions."""
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
from day29_persistence import PersistentBoundary, ReplayLedger
from tests import test_day27_release as fixtures


def worker(path, barrier, output):
    fixture = fixtures.ReleaseQueueTests()
    fixture.setUp()
    boundary = PersistentBoundary(fixture.state, ReplayLedger(path))
    receipt = boundary.accept('job:29', boundary.prepare(), 'candidate-marker',
                              original=Decision(False, None, ('blocked',)), now=1000)
    barrier.wait(10)
    result = boundary.deliver(receipt.delivery_id, recipient='owner:alice', task=TASK, now=1001)
    output.put((result.released, result.reason))


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'ledger.sqlite'
        ReplayLedger.provision(self.path)
        fixture = fixtures.ReleaseQueueTests()
        fixture.setUp()
        self.state = fixture.state
        self.restart()

    def restart(self):
        self.boundary = PersistentBoundary(self.state, ReplayLedger(self.path))

    def accept(self, operation='job:29'):
        return self.boundary.accept(operation, self.boundary.prepare(), 'candidate-marker',
                                    original=Decision(False, None, ('blocked',)), now=self.state.snapshot.now)

    def send(self, receipt, **changes):
        args = dict(recipient='owner:alice', task=TASK, now=1001)
        args.update(changes)
        return self.boundary.deliver(receipt.delivery_id, **args)

    def denied(self, result):
        self.assertFalse(result.released)
        self.assertIsNone(result.text)
        self.assertIsNone(result.snapshot_sha256)
        self.assertIsNone(result.candidate_sha256)
        self.assertEqual(result.provenance, ())
        self.assertEqual(result.original_reasons, ())

    def test_duplicate_after_reopen_and_fresh_clock(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('offline only')):
            self.assertTrue(self.send(self.accept()).released)
        self.state = replace(self.state, snapshot=replace(self.state.snapshot, now=1001))
        self.restart()
        result = self.send(self.accept())
        self.denied(result)
        self.assertEqual(result.reason, 'consumed_operation_id')
        self.assertTrue(self.send(self.accept('job:30')).released)
        self.assertNotIn(b'candidate-marker', self.path.read_bytes())
        self.assertNotIn(b'23 minutes', self.path.read_bytes())

    def test_pending_restart_requires_fresh_admission(self):
        receipt = self.accept()
        self.restart()
        self.denied(self.send(receipt))
        self.assertTrue(self.send(self.accept()).released)

    def test_two_processes_have_one_winner(self):
        ctx = multiprocessing.get_context('spawn')
        barrier, output = ctx.Barrier(2), ctx.Queue()
        processes = [ctx.Process(target=worker, args=(str(self.path), barrier, output))
                     for _ in range(2)]
        try:
            for process in processes:
                process.start()
            results = [output.get(timeout=20) for _ in processes]
            for process in processes:
                process.join(20)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(sum(released for released, _ in results), 1)
            self.assertIn((False, 'consumed_operation_id'), results)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            output.close()

    def test_wrong_recipient_and_task_do_not_claim(self):
        receipt = self.accept()
        self.denied(self.send(receipt, recipient='owner:bob'))
        self.denied(self.send(receipt, task='other'))
        self.assertTrue(self.send(receipt).released)

    def test_consumed_id_cannot_be_rebound(self):
        self.assertTrue(self.send(self.accept()).released)
        self.state = replace(self.state, snapshot=replace(self.state.snapshot, principal='owner:bob'),
                             lease=replace(self.state.lease, policy=replace(self.state.lease.policy,
                                 grants=(replace(self.state.lease.policy.grants[0], principal='owner:bob'),))))
        self.restart()
        result = self.send(self.accept(), recipient='owner:bob')
        self.denied(result)
        self.assertEqual(result.reason, 'operation_binding_mismatch')

    def test_revocation_before_dispatch(self):
        receipt = self.accept()
        self.boundary.update(replace(self.state, authority=Authority(5, ('lease:27',))))
        self.denied(self.send(receipt))
        self.restart()
        self.assertTrue(self.send(self.accept()).released)

    def test_invalid_storage_and_schema(self):
        for kind in ('missing', 'corrupt', 'schema', 'version'):
            with self.subTest(kind=kind):
                self.path.unlink()
                if kind == 'corrupt':
                    self.path.write_bytes(b'not a database')
                elif kind in ('schema', 'version'):
                    ReplayLedger.provision(self.path)
                    with closing(sqlite3.connect(self.path)) as db, db:
                        db.execute('DROP TABLE claims' if kind == 'schema' else 'PRAGMA user_version=1')
                self.restart()
                self.denied(self.send(self.accept()))
                if not self.path.exists():
                    self.path.touch()

    def test_locked_storage_fails_closed(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            self.denied(self.send(self.accept()))

    def test_commit_failure_returns_no_text(self):
        connect = sqlite3.connect
        for committed in (False, True):
            with self.subTest(committed=committed):
                operation = 'commit:' + str(committed)
                class Connection:
                    def __init__(self, *args, **kwargs):
                        self.db = connect(*args, **kwargs)
                    def execute(self, *args):
                        return self.db.execute(*args)
                    def commit(self):
                        if committed:
                            self.db.commit()
                        raise sqlite3.OperationalError('simulated commit uncertainty')
                    def close(self):
                        self.db.close()
                with patch('day29_persistence.sqlite3.connect', side_effect=Connection):
                    self.denied(self.send(self.accept(operation)))
                self.restart()
                result = self.send(self.accept(operation))
                self.assertEqual(result.released, not committed)
                if committed:
                    self.denied(result)

    def test_crash_before_and_after_commit(self):
        # Abrupt exit, no context manager rollback or connection close.
        for committed in (False, True):
            with self.subTest(committed=committed):
                operation = 'crash:' + str(committed)
                script = '''import os, sqlite3, sys
from day29_persistence import ReplayLedger
if sys.argv[3] == 'True':
    assert ReplayLedger(sys.argv[1]).claim(sys.argv[2], 'binding') is None
else:
    db = sqlite3.connect(sys.argv[1])
    db.execute('PRAGMA synchronous=FULL')
    db.execute('BEGIN IMMEDIATE')
    db.execute('INSERT INTO claims VALUES (?, ?)', (sys.argv[2], 'binding'))
os._exit(29)
'''
                process = subprocess.run([sys.executable, '-B', '-S', '-c', script,
                                          str(self.path), operation, str(committed)], check=False)
                self.assertEqual(process.returncode, 29)
                result = ReplayLedger(self.path).claim(operation, 'binding')
                self.assertEqual(result, 'consumed_operation_id' if committed else None)

    def test_provision_never_overwrites_and_invalid_ids(self):
        with self.assertRaises(FileExistsError):
            ReplayLedger.provision(self.path)
        for operation in ('', None, [], True, 'x' * 129):
            self.assertIsNone(self.accept(operation))
