"""End-to-end offline delivery through both SQLite databases."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import socket
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
from day30_outbox import Outbox
from day31_receiver import Receiver
from day32_delivery import Attempt, Fault, OfflineTransport, deliver
from tests import test_day27_release as fixtures


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.sender_path = Path(directory) / 'sender.sqlite'
        self.receiver_path = Path(directory) / 'receiver.sqlite'
        Outbox.provision(self.sender_path)
        Receiver.provision(self.receiver_path)
        fixture = fixtures.ReleaseQueueTests()
        fixture.setUp()
        self.state = fixture.state
        self.restart()
        self.enqueue('job:32')

    def restart(self):
        self.box = Outbox(self.state, self.sender_path)
        self.receiver = Receiver(self.receiver_path, recipient='owner:alice', task=TASK)

    def enqueue(self, key):
        self.assertTrue(self.box.enqueue(key, self.box.prepare(), 'discarded-candidate',
                                        original=Decision(False, None, ('blocked',)), now=1000))

    def attempt(self, now, fault=Fault.NONE, **overrides):
        args = dict(operation_id='job:32', recipient='owner:alice', task=TASK,
                    now=now, transport=OfflineTransport(fault))
        return deliver(self.box, self.receiver, **(args | overrides))

    def query(self, path, sql):
        with closing(sqlite3.connect(path)) as db:
            return db.execute(sql).fetchall()

    def execute(self, path, sql):
        with closing(sqlite3.connect(path)) as db, db:
            db.execute(sql)

    def sender_rows(self):
        return self.query(self.sender_path, 'SELECT status, attempts FROM outbox ORDER BY operation_id')

    def assert_empty_receiver(self):
        self.assertEqual(self.query(self.receiver_path, 'SELECT * FROM receipts'), [])
        self.assertEqual(self.query(self.receiver_path, 'SELECT * FROM effects'), [])

    def assert_one_effect(self):
        [(payload,)] = self.query(self.sender_path, "SELECT text FROM outbox WHERE operation_id='job:32'")
        self.assertIn('23 minutes', payload)
        self.assertNotIn('discarded-candidate', payload)
        self.assertEqual(self.query(self.receiver_path, 'SELECT * FROM receipts'),
                         [('job:32', 'owner:alice', TASK, payload)])
        self.assertEqual(self.query(self.receiver_path, 'SELECT * FROM effects'),
                         [('job:32', payload)])

    def test_lost_ack_and_duplicate_frames_across_restart(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('offline only')):
            self.assertEqual(self.attempt(1001, Fault.LOST_ACK), Attempt('ack_lost', ('applied',)))
            self.assertEqual(self.sender_rows(), [('leased', 1)])
            self.assert_one_effect()
            self.restart()
            self.assertEqual(self.attempt(1005), Attempt('claim_unavailable'))
            self.assertEqual(self.attempt(1006, Fault.DUPLICATE_MESSAGE),
                             Attempt('done', ('duplicate', 'duplicate')))
        self.assertEqual(self.sender_rows(), [('done', 2)])
        self.assert_one_effect()

    def test_temporary_transport_failure_then_duplicate_first_delivery(self):
        self.assertEqual(self.attempt(1001, Fault.TRANSPORT_UNAVAILABLE),
                         Attempt('transport_unavailable'))
        self.assert_empty_receiver()
        self.assertEqual(self.sender_rows(), [('leased', 1)])
        self.restart()
        self.assertEqual(self.attempt(1006, Fault.DUPLICATE_MESSAGE),
                         Attempt('done', ('applied', 'duplicate')))
        self.assertEqual(self.sender_rows(), [('done', 2)])
        self.assert_one_effect()

    def test_fresh_process_reconciles_committed_effect(self):
        self.assertEqual(self.attempt(1001, Fault.LOST_ACK), Attempt('ack_lost', ('applied',)))
        script = """
import sys
from day24_recovery import TASK
from day30_outbox import Outbox
from day31_receiver import Receiver
from day32_delivery import Attempt, deliver
from tests.test_day27_release import ReleaseQueueTests

fixture = ReleaseQueueTests()
fixture.setUp()
box = Outbox(fixture.state, sys.argv[1])
receiver = Receiver(sys.argv[2], recipient='owner:alice', task=TASK)
result = deliver(box, receiver, 'job:32', recipient='owner:alice', task=TASK, now=1006)
if result != Attempt('done', ('duplicate',)):
    raise SystemExit(repr(result))
"""
        child = subprocess.run([sys.executable, '-B', '-S', '-c', script,
                                str(self.sender_path), str(self.receiver_path)],
                               cwd=Path(__file__).resolve().parents[1],
                               capture_output=True, text=True, timeout=15)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(self.sender_rows(), [('done', 2)])
        self.assert_one_effect()

    def test_concurrent_retries_after_receiver_commit(self):
        self.assertEqual(self.attempt(1001, Fault.LOST_ACK), Attempt('ack_lost', ('applied',)))
        barrier = Barrier(2)

        def retry():
            box = Outbox(self.state, self.sender_path)
            receiver = Receiver(self.receiver_path, recipient='owner:alice', task=TASK)
            barrier.wait(timeout=10)
            return deliver(box, receiver, 'job:32', recipient='owner:alice', task=TASK, now=1006)

        with ThreadPoolExecutor(max_workers=2) as workers:
            attempts = [workers.submit(retry) for _ in range(2)]
            self.assertCountEqual([attempt.result(timeout=15) for attempt in attempts],
                                  [Attempt('done', ('duplicate',)), Attempt('claim_unavailable')])
        self.assertEqual(self.sender_rows(), [('done', 2)])
        self.assert_one_effect()

    def test_invalid_frames_never_reach_receiver_even_with_valid_prefix(self):
        self.enqueue('job:other')
        changes = (
            {'operation_id': 'job:other'}, {'token': 'different-token'},
            {'recipient': 'owner:bob'}, {'task': 'different-task'},
            {'payload': 'different-payload'}, {'payload': b'wrong-type'},
        )
        for offset, fields in enumerate(changes):
            with self.subTest(fields=fields):
                key = f'tamper:{offset}'
                self.enqueue(key)
                with patch.object(OfflineTransport, 'frames', autospec=True,
                                  side_effect=lambda _, message: (message, replace(message, **fields))):
                    self.assertEqual(self.attempt(1001, operation_id=key), Attempt('invalid_message'))
                self.assert_empty_receiver()
        self.assertEqual(self.sender_rows(), [('pending', 0)] * 2 + [('leased', 1)] * len(changes))

    def test_invalid_route_or_key_and_unauthorized_retry_fail_closed(self):
        for overrides in ({'recipient': 'owner:bob'}, {'task': 'different-task'},
                          {'operation_id': ''}, {'operation_id': 'unknown'}):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.attempt(1001, **overrides), Attempt('claim_unavailable'))
        self.assertEqual(self.sender_rows(), [('pending', 0)])
        self.assertEqual(self.attempt(1001, Fault.TRANSPORT_UNAVAILABLE),
                         Attempt('transport_unavailable'))
        self.state = replace(self.state, authority=Authority(5, ('lease:27',)))
        self.restart()
        self.assertEqual(self.attempt(1006), Attempt('claim_unavailable'))
        self.assertEqual(self.sender_rows(), [('leased', 1)])
        self.assert_empty_receiver()

    def test_sender_claim_failure_leaves_receiver_untouched(self):
        with closing(sqlite3.connect(self.sender_path)) as db:
            db.execute('BEGIN IMMEDIATE')
            self.assertEqual(self.attempt(1001), Attempt('claim_unavailable'))
        self.assertEqual(self.sender_rows(), [('pending', 0)])
        self.assert_empty_receiver()
        self.assertEqual(self.attempt(1002), Attempt('done', ('applied',)))
        self.assert_one_effect()

    def test_receiver_route_mismatch_prevents_ack(self):
        self.receiver = Receiver(self.receiver_path, recipient='owner:bob', task=TASK)
        self.assertEqual(self.attempt(1001), Attempt('receiver_unconfirmed'))
        self.assertEqual(self.sender_rows(), [('leased', 1)])
        self.assert_empty_receiver()
        self.restart()
        self.assertEqual(self.attempt(1006), Attempt('done', ('applied',)))
        self.assert_one_effect()

    def test_receiver_rollback_then_sender_ack_failure_then_recovery(self):
        self.execute(self.receiver_path, """
            CREATE TRIGGER fail_effect BEFORE INSERT ON effects
            BEGIN SELECT RAISE(ABORT, 'injected effect failure'); END
        """)
        self.assertEqual(self.attempt(1001), Attempt('receiver_unconfirmed'))
        self.assert_empty_receiver()
        self.assertEqual(self.sender_rows(), [('leased', 1)])
        self.execute(self.receiver_path, 'DROP TRIGGER fail_effect')
        self.execute(self.sender_path, """
            CREATE TRIGGER fail_ack BEFORE UPDATE ON outbox WHEN NEW.status = 'done'
            BEGIN SELECT RAISE(ABORT, 'injected acknowledgement failure'); END
        """)
        self.assertEqual(self.attempt(1006), Attempt('ack_unconfirmed', ('applied',)))
        self.assertEqual(self.sender_rows(), [('leased', 2)])
        self.assert_one_effect()
        self.execute(self.sender_path, 'DROP TRIGGER fail_ack')
        self.restart()
        self.assertEqual(self.attempt(1011), Attempt('done', ('duplicate',)))
        self.assertEqual(self.sender_rows(), [('done', 3)])
        self.assert_one_effect()

    def test_retry_budget_can_leave_no_effect(self):
        for now in (1001, 1006, 1011):
            self.assertEqual(self.attempt(now, Fault.TRANSPORT_UNAVAILABLE),
                             Attempt('transport_unavailable'))
        self.assertEqual(self.attempt(1016), Attempt('claim_unavailable'))
        self.assertEqual(self.sender_rows(), [('leased', 3)])
        self.assert_empty_receiver()
