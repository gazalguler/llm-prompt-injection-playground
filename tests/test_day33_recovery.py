"""Process interruption and recovery through the Day 32 offline delivery path."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest
from unittest.mock import patch

from day21_gate import Decision
from day24_recovery import TASK
from day26_lifecycle import Authority
from day30_outbox import Outbox, context
from day31_receiver import Receiver
from day32_delivery import Attempt, Fault, OfflineTransport, deliver
from tests import test_day27_release as fixtures


KEY = 'job:33'
RECIPIENT = 'owner:alice'
ORIGINAL = Decision(False, None, ('blocked',))

# Stop before commit after the operation's SQL has executed, or after commit
# before control returns to the caller. The real context manager owns the commit.
CRASH_WORKER = """
from contextlib import contextmanager
import os
import sys

from tests.test_day33_recovery import make_workers, enqueue, attempt

sender_path, receiver_path, operation, edge = sys.argv[1:]
_, box, receiver = make_workers(sender_path, receiver_path)
target = receiver if operation == 'receiver' else box
transaction = target._transaction
transaction_number = 2 if operation == 'ack' else 1
calls = 0

@contextmanager
def interrupt():
    global calls
    calls += 1
    selected = calls == transaction_number
    with transaction() as db:
        yield db
        if selected and edge == 'before':
            os._exit(33)
    if selected and edge == 'after':
        os._exit(33)

target._transaction = interrupt
if operation == 'enqueue':
    enqueue(box)
else:
    attempt(box, receiver, 1001)
raise SystemExit('worker returned before reaching the fault point')
"""


def make_workers(sender_path, receiver_path):
    fixture = fixtures.ReleaseQueueTests()
    fixture.setUp()
    return (fixture.state, Outbox(fixture.state, sender_path),
            Receiver(receiver_path, recipient=RECIPIENT, task=TASK))


def enqueue(box):
    return box.enqueue(KEY, box.prepare(), 'discarded-candidate', original=ORIGINAL, now=1000)


def attempt(box, receiver, now, fault=Fault.NONE):
    return deliver(box, receiver, KEY, recipient=RECIPIENT, task=TASK, now=now,
                   transport=OfflineTransport(fault))


class RecoveryTests(unittest.TestCase):
    def provision(self, directory):
        self.sender = Path(directory) / 'sender.sqlite'
        self.receiver = Path(directory) / 'receiver.sqlite'
        Outbox.provision(self.sender)
        Receiver.provision(self.receiver)
        return self.reopen()

    def reopen(self):
        self.state, box, receiver = make_workers(self.sender, self.receiver)
        return box, receiver

    def crash(self, operation, edge):
        worker = subprocess.run(
            [sys.executable, '-B', '-S', '-c', CRASH_WORKER, str(self.sender),
             str(self.receiver), operation, edge],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(worker.returncode, 33, worker.stderr)

    def rows(self, path, sql):
        with closing(sqlite3.connect(path)) as db:
            return db.execute(sql).fetchall()

    def assert_snapshot(self, status, attempts, *, effect=False):
        sender = self.rows(self.sender,
                           'SELECT operation_id, context, text, status, attempts FROM outbox')
        receipts = self.rows(self.receiver, 'SELECT * FROM receipts')
        effects = self.rows(self.receiver, 'SELECT * FROM effects')
        if status is None:
            self.assertEqual(sender, [])
            self.assertEqual(receipts, [])
            self.assertEqual(effects, [])
            return
        [(key, binding, payload, stored_status, stored_attempts)] = sender
        self.assertEqual((key, binding), (KEY, context(self.state)))
        self.assertIn('23 minutes', payload)
        self.assertNotIn('discarded-candidate', payload)
        self.assertEqual((stored_status, stored_attempts), (status, attempts))
        self.assertEqual(receipts, [(KEY, RECIPIENT, TASK, payload)] if effect else [])
        self.assertEqual(effects, [(KEY, payload)] if effect else [])
        return payload

    def test_enqueue_commit_boundaries(self):
        for edge, status in (('before', None), ('after', 'pending')):
            with self.subTest(edge=edge), TemporaryDirectory() as directory:
                self.provision(directory)
                self.crash('enqueue', edge)
                box, receiver = self.reopen()
                original_payload = self.assert_snapshot(status, 0)
                self.assertTrue(enqueue(box))
                if original_payload is not None:
                    self.assertEqual(self.assert_snapshot('pending', 0), original_payload)
                self.assertEqual(attempt(box, receiver, 1001), Attempt('done', ('applied',)))
                self.assert_snapshot('done', 1, effect=True)

    def test_delivery_commit_boundaries(self):
        cases = (
            ('claim', 'before', 'pending', 0, False),
            ('claim', 'after', 'leased', 1, False),
            ('receiver', 'before', 'leased', 1, False),
            ('receiver', 'after', 'leased', 1, True),
            ('ack', 'before', 'leased', 1, True),
            ('ack', 'after', 'done', 1, True),
        )
        for operation, edge, status, count, effect in cases:
            with self.subTest(operation=operation, edge=edge), TemporaryDirectory() as directory:
                box, _ = self.provision(directory)
                self.assertTrue(enqueue(box))
                payload = self.assert_snapshot('pending', 0)
                self.crash(operation, edge)
                box, receiver = self.reopen()
                self.assertEqual(self.assert_snapshot(status, count, effect=effect), payload)
                if status == 'leased':
                    self.assertEqual(attempt(box, receiver, 1005), Attempt('claim_unavailable'))
                    self.assertEqual(self.assert_snapshot(status, count, effect=effect), payload)
                result = attempt(box, receiver, 1006)
                if status == 'done':
                    self.assertEqual(result, Attempt('claim_unavailable'))
                else:
                    expected = 'duplicate' if effect else 'applied'
                    self.assertEqual(result, Attempt('done', (expected,)))
                    count += 1
                self.assertEqual(self.assert_snapshot('done', count, effect=True), payload)

    def test_lost_ack_reclaim_fences_old_token_during_concurrent_retry(self):
        with TemporaryDirectory() as directory:
            box, receiver = self.provision(directory)
            self.assertTrue(enqueue(box))
            claims = []
            original_claim = box.claim

            def record(*args, **kwargs):
                claim = original_claim(*args, **kwargs)
                claims.append(claim)
                return claim

            with patch.object(box, 'claim', side_effect=record):
                self.assertEqual(attempt(box, receiver, 1001, Fault.LOST_ACK),
                                 Attempt('ack_lost', ('applied',)))
            [stale] = claims
            self.assert_snapshot('leased', 1, effect=True)
            first = self.reopen()
            second = self.reopen()
            ready = Barrier(2)

            def retry(workers):
                ready.wait(timeout=10)
                return attempt(*workers, 1006)

            original_receive = Receiver.receive

            def receive(instance, claim, **route):
                self.assertNotEqual(claim.token, stale.token)
                self.assertFalse(box.ack(stale, now=1006))
                self.assertFalse(box.ack(replace(claim, token='wrong-token'), now=1006))
                self.assert_snapshot('leased', 2, effect=True)
                return original_receive(instance, claim, **route)

            with patch.object(Receiver, 'receive', autospec=True, side_effect=receive):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(retry, workers) for workers in (first, second)]
                    self.assertCountEqual([future.result(timeout=15) for future in futures],
                                          [Attempt('done', ('duplicate',)),
                                           Attempt('claim_unavailable')])
            self.assert_snapshot('done', 2, effect=True)

    def test_altered_identity_then_revocation_preserves_committed_binding(self):
        with TemporaryDirectory() as directory:
            box, receiver = self.provision(directory)
            self.assertTrue(enqueue(box))
            self.assertEqual(attempt(box, receiver, 1001, Fault.LOST_ACK),
                             Attempt('ack_lost', ('applied',)))
            payload = self.assert_snapshot('leased', 1, effect=True)
            box, receiver = self.reopen()
            with (
                patch.object(OfflineTransport, 'frames', autospec=True,
                             side_effect=lambda _, frame: (replace(frame, operation_id='other'),)),
                patch.object(receiver, 'receive', wraps=receiver.receive) as receive,
                patch.object(box, 'ack', wraps=box.ack) as ack,
            ):
                self.assertEqual(attempt(box, receiver, 1006), Attempt('invalid_message'))
                receive.assert_not_called()
                ack.assert_not_called()
            self.assertEqual(self.assert_snapshot('leased', 2, effect=True), payload)
            revoked = replace(self.state, authority=Authority(5, ('lease:27',)))
            box.update(revoked)
            with patch.object(receiver, 'receive', wraps=receiver.receive) as receive:
                self.assertEqual(attempt(box, receiver, 1011), Attempt('claim_unavailable'))
                receive.assert_not_called()
            self.assertEqual(self.assert_snapshot('leased', 2, effect=True), payload)

    def test_outage_exhausts_attempts_even_after_transport_recovers(self):
        with TemporaryDirectory() as directory:
            box, receiver = self.provision(directory)
            self.assertTrue(enqueue(box))
            for count, now in enumerate((1001, 1006, 1011), start=1):
                self.assertEqual(attempt(box, receiver, now, Fault.TRANSPORT_UNAVAILABLE),
                                 Attempt('transport_unavailable'))
                self.assert_snapshot('leased', count)
                box, receiver = self.reopen()
            self.assertEqual(attempt(box, receiver, 1016), Attempt('claim_unavailable'))
            self.assert_snapshot('leased', 3)
