"""Contract regressions for the offline sender, transport and receiver."""
from contextlib import closing
from dataclasses import replace
from types import SimpleNamespace
import sqlite3
from unittest.mock import patch
import unittest

from day24_recovery import TASK
from day31_receiver import dispatch
from day32_delivery import Attempt, Fault, OfflineTransport
from tests.test_day32_delivery import DeliveryFixture


class ContractTests(DeliveryFixture, unittest.TestCase):
    route = {'recipient': 'owner:alice', 'task': TASK}

    def sender_row(self):
        [row] = self.query(self.sender_path, 'SELECT * FROM outbox')
        return row

    def assert_retry(self):
        self.restart()
        leased = self.sender_row()
        self.assertEqual(self.attempt(1005), Attempt('claim_unavailable'))
        self.assertEqual(self.sender_row(), leased)
        self.assertEqual(self.attempt(1006), Attempt('done', ('applied',)))
        done = self.sender_row()
        self.assertEqual(done[:4], leased[:4])
        self.assertEqual((done[4], done[7]), ('done', 2))
        self.assert_one_effect()

    def test_missing_transport_members_leave_intent_pending(self):
        pending = self.sender_row()
        for transport in (object(), SimpleNamespace(fault=Fault.NONE),
                          SimpleNamespace(fault=Fault.NONE, frames=())):
            with self.subTest(transport=transport):
                self.assertEqual(self.attempt(1001, transport=transport),
                                 Attempt('invalid_transport'))
                self.assertEqual(self.sender_row(), pending)
                self.assert_empty_receiver()
        self.restart()
        self.assertEqual(self.attempt(1001), Attempt('done', ('applied',)))
        self.assert_one_effect()

    def test_transport_response_shapes_and_frame_bindings(self):
        cases = (
            ('none', lambda message: None),
            ('list', lambda message: [message]),
            ('empty tuple', lambda message: ()),
            ('missing payload', lambda message: (message, SimpleNamespace(
                operation_id=message.operation_id, token=message.token,
                recipient=message.recipient, task=message.task))),
            ('wrong operation', lambda message: (message, replace(message, operation_id='job:other'))),
            ('wrong recipient', lambda message: (message, replace(message, recipient='owner:bob'))),
            ('wrong task', lambda message: (message, replace(message, task='other'))),
            ('wrong payload', lambda message: (message, replace(message, payload='other'))),
            ('wrong token type', lambda message: (message, replace(message, token=42))),
        )
        pending = self.sender_row()
        for label, frames in cases:
            with self.subTest(case=label):
                # Give each response the same fresh pending intent.
                self.execute(self.sender_path, 'DELETE FROM outbox')
                self.enqueue('job:32')
                with patch.object(OfflineTransport, 'frames', side_effect=frames):
                    status = 'transport_unavailable' if label == 'empty tuple' else 'invalid_message'
                    self.assertEqual(self.attempt(1001), Attempt(status))
                leased = self.sender_row()
                self.assertEqual(leased[:4], pending[:4])
                self.assertIs(type(leased[5]), str)
                self.assertTrue(leased[5])
                self.assertEqual((leased[4], *leased[6:]), ('leased', 1006, 1, 1001))
                self.assert_empty_receiver()
        self.assert_retry()

    def test_unknown_persisted_status_cannot_be_claimed_after_reopen(self):
        for status in ('unexpected', ''):
            with self.subTest(status=status):
                with closing(sqlite3.connect(self.sender_path)) as db, db:
                    db.execute('UPDATE outbox SET status=?', (status,))
                self.restart()
                rejected = self.sender_row()
                self.assertEqual(self.attempt(1001), Attempt('claim_unavailable'))
                self.assertEqual(self.sender_row(), rejected)
                self.assert_empty_receiver()
        self.execute(self.sender_path, "UPDATE outbox SET status='pending'")
        self.restart()
        self.assertEqual(self.attempt(1001), Attempt('done', ('applied',)))
        self.assert_one_effect()

    def test_ack_rejects_operation_id_coerced_by_sqlite(self):
        self.enqueue('37')
        claim = self.box.claim('37', **self.route, now=1001)
        self.assertIsNotNone(claim)
        rows = self.query(self.sender_path, 'SELECT * FROM outbox ORDER BY operation_id')
        for changes in ({'operation_id': 37}, {'token': None}, {'token': claim.token.encode()}):
            with self.subTest(changes=changes):
                self.assertIs(self.box.ack(replace(claim, **changes), now=1001), False)
                self.assertEqual(self.query(self.sender_path, 'SELECT * FROM outbox ORDER BY operation_id'),
                                 rows)
                self.assert_empty_receiver()
        self.restart()
        self.assertEqual(self.attempt(1006, operation_id='37'), Attempt('done', ('applied',)))

    def test_receiver_rejects_incomplete_or_mistyped_claim_outcome(self):
        claim = self.box.claim('job:32', **self.route, now=1001)
        self.assertIsNotNone(claim)
        leased = self.sender_row()
        for outcome in (SimpleNamespace(text=claim.outcome.text),
                        SimpleNamespace(released=True),
                        replace(claim.outcome, text=b'payload'),
                        replace(claim.outcome, released='false'),
                        replace(claim.outcome, released=1)):
            with self.subTest(outcome=outcome):
                self.assertIsNone(self.receiver.receive(replace(claim, outcome=outcome), **self.route))
                self.assertEqual(self.sender_row(), leased)
                self.assert_empty_receiver()
        self.assert_retry()

    def test_unrecognized_receiver_results_do_not_acknowledge(self):
        class ReceiverStatus(str):
            pass

        for send in (dispatch_adapter, deliver_attempt):
            for status in (False, 'pending', ReceiverStatus('applied')):
                with self.subTest(sender=send.__name__, status=status):
                    self.execute(self.sender_path, 'DELETE FROM outbox')
                    self.enqueue('job:32')
                    with patch.object(self.receiver, 'receive', return_value=status):
                        self.assertEqual(send(self), False if send is dispatch_adapter
                                         else Attempt('receiver_unconfirmed'))
                    self.assertEqual(self.sender_row()[4], 'leased')
                    self.assert_empty_receiver()
        self.assert_retry()

    def test_stored_versions_and_table_definitions_are_checked_on_reopen(self):
        pending = self.sender_row()
        self.execute(self.sender_path, 'PRAGMA user_version=31')
        self.restart()
        self.assertEqual(self.attempt(1001), Attempt('claim_unavailable'))
        self.assertEqual(self.sender_row(), pending)
        self.assert_empty_receiver()
        self.execute(self.sender_path, 'PRAGMA user_version=30')

        self.execute(self.receiver_path, 'ALTER TABLE effects ADD COLUMN extra TEXT')
        self.restart()
        self.assertEqual(self.attempt(1001), Attempt('receiver_unconfirmed'))
        self.assertEqual(self.sender_row()[4], 'leased')
        self.assert_empty_receiver()
        self.execute(self.receiver_path, 'ALTER TABLE effects DROP COLUMN extra')
        self.assert_retry()


def dispatch_adapter(case):
    return dispatch(case.box, case.receiver, 'job:32', **case.route, now=1001)


def deliver_attempt(case):
    return case.attempt(1001)
