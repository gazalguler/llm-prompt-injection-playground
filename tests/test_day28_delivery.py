"""Synthetic delivery handoffs; no model calls or external transport."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from threading import Barrier, Event
import socket
import unittest
from unittest.mock import patch
from day21_gate import Decision
from day24_recovery import TASK, record_digest
from day25_authorization import SourcePolicy
from day26_lifecycle import Authority
from day28_delivery import DeliveryBoundary, recover_with_lease
from tests import test_day27_release as fixtures


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.ReleaseQueueTests()
        fixture.setUp()
        self.state = fixture.state
        self.boundary = DeliveryBoundary(self.state)
        self.receipt = self.accept()

    def accept(self, now=1000, candidate='private-candidate-marker', original=None):
        return self.boundary.accept(
            self.boundary.prepare(), candidate, now=now,
            original=original if original is not None else Decision(False, None, ('blocked',)))

    def deliver(self, receipt=None, **kwargs):
        args = dict(recipient='owner:alice', task=TASK, now=1001)
        args.update(kwargs)
        return self.boundary.deliver(
            (receipt or self.receipt).delivery_id, **args)

    def assertDenied(self, result):
        self.assertFalse(result.released)
        self.assertIsNone(result.text)
        self.assertIsNone(result.snapshot_sha256)
        self.assertIsNone(result.candidate_sha256)
        self.assertEqual(result.provenance, ())
        self.assertEqual(result.original_reasons, ())
        self.assertNotIn('private-candidate-marker', repr(result))
        self.assertNotIn('23 minutes', repr(result))

    def test_text_free_admission_and_offline_handoff_audit(self):
        self.assertNotIn('23 minutes', repr(self.receipt))
        self.assertNotIn('private-candidate-marker', repr(self.receipt))
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            result = self.deliver()
        self.assertTrue(result.released)
        self.assertIn('23 minutes', result.text)
        self.assertNotIn('private-candidate-marker', result.text)
        self.assertEqual(result.policy, 'day28-delivery-boundary-v1')
        self.assertEqual(result.original_reasons, ('blocked',))
        self.assertEqual(result.provenance, (('owner:telemetry', 7, 'verified:27'),))
        self.assertIsNotNone(result.candidate_sha256)
        self.assertIsNotNone(result.snapshot_sha256)

    def test_duplicate_and_distinct_identifiers(self):
        second = self.accept()
        self.assertNotEqual(self.receipt.delivery_id, second.delivery_id)
        self.assertTrue(self.deliver().released)
        self.assertEqual(self.deliver().reason, 'consumed_delivery_id')
        self.assertDenied(self.deliver())
        self.assertTrue(self.deliver(second).released)

    def test_parallel_delivery_has_one_winner(self):
        barrier = Barrier(12)
        def send(_):
            barrier.wait()
            return self.deliver()
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(send, range(12)))
        self.assertEqual(sum(r.released for r in results), 1)
        for result in results:
            if not result.released:
                self.assertDenied(result)
                self.assertEqual(result.reason, 'consumed_delivery_id')

    def test_revoked_or_withdrawn_state(self):
        for state in (replace(self.state, authority=Authority(5, ('lease:27',))),
                      replace(self.state, snapshot=replace(self.state.snapshot, authorized=False)),
                      replace(self.state, lease=replace(self.state.lease, policy=SourcePolicy(()))),
                      None):
            with self.subTest(state=repr(state)):
                self.boundary.update(state)
                self.assertDenied(self.deliver())
                self.assertIsNone(self.accept())
        self.boundary.update(self.state)
        self.assertTrue(self.deliver(self.accept()).released)

    def test_expiry_freshness_and_clock_rollback(self):
        for now in (999, 1040, 1100, True, None, '1001'):
            with self.subTest(now=now):
                self.assertDenied(self.deliver(now=now))
        receipt = self.accept(now=1005)
        self.assertDenied(self.deliver(receipt, now=1004))
        # Give the lease a longer life so source freshness is tested separately.
        state = replace(self.state, lease=replace(self.state.lease, expires_at=1090))
        self.boundary = DeliveryBoundary(state)
        receipt = self.accept()
        second = self.accept()
        self.assertTrue(self.deliver(receipt, now=1055).released)
        self.assertEqual(self.deliver(second, now=1056).reason, 'stale_or_future_facts')

    def test_record_and_source_replacement_with_updated_grant(self):
        for changes in (dict(revision=8, duration_minutes=24), dict(source_id='owner:monitor')):
            with self.subTest(changes=changes):
                r = replace(self.state.snapshot.records[0], **changes)
                p = replace(self.state.snapshot.pins[0], source_id=r.source_id,
                            revision=r.revision, record_sha256=record_digest(r))
                g = replace(self.state.lease.policy.grants[0], source_id=r.source_id,
                            revision=r.revision, record_sha256=p.record_sha256)
                state = replace(self.state, snapshot=replace(self.state.snapshot, records=(r,), pins=(p,)),
                                lease=replace(self.state.lease, policy=SourcePolicy((g,))))
                self.boundary.update(state)
                self.assertDenied(self.deliver())
                self.assertTrue(self.deliver(self.accept()).released)

    def test_aba_and_unrelated_update_fail_closed(self):
        self.boundary.update(replace(self.state, authority=Authority(5, ())))
        self.boundary.update(self.state)
        self.assertDenied(self.deliver())
        receipt = self.accept()
        self.boundary.update(self.state)
        self.assertDenied(self.deliver(receipt))

    def test_cross_recipient_and_task_replay(self):
        for args in (dict(recipient='owner:bob'), dict(task='different_task'),
                     dict(recipient=None), dict(task=[])):
            with self.subTest(args=args):
                self.assertDenied(self.deliver(**args))
        self.assertTrue(self.deliver().released)

    def test_tampered_foreign_and_malformed_identifiers(self):
        for token in (self.receipt.delivery_id + 'x', '', None, [], {}):
            with self.subTest(token=token):
                self.assertDenied(self.boundary.deliver(token, recipient='owner:alice', task=TASK, now=1001))
        other = DeliveryBoundary(self.state)
        self.assertDenied(other.deliver(self.receipt.delivery_id, recipient='owner:alice', task=TASK, now=1001))
        with self.assertRaises(FrozenInstanceError):
            self.receipt.recipient = 'owner:bob'
        forged = replace(self.receipt, recipient='owner:bob')
        self.assertDenied(self.deliver(forged, recipient=forged.recipient))
        self.assertTrue(self.deliver().released)

    def test_day27_rejection_and_discard_contract(self):
        self.assertIsNone(self.accept(original=Decision(True, 'private-candidate-marker', ())))
        foreign = DeliveryBoundary(self.state).prepare()
        self.assertIsNone(self.boundary.accept(foreign, '', original=Decision(False, None, ('blocked',)), now=1000))
        ticket = self.boundary.prepare()
        self.boundary.update(self.state)
        self.assertIsNone(self.boundary.accept(ticket, '', original=Decision(False, None, ('blocked',)), now=1000))

    def test_update_and_delivery_share_boundary_lock(self):
        entered, proceed, updating = Event(), Event(), Event()
        def validate(*args, **kwargs):
            entered.set()
            self.assertTrue(proceed.wait(5))
            return recover_with_lease(*args, **kwargs)
        def revoke():
            updating.set()
            self.boundary.update(replace(self.state, authority=Authority(5, ('lease:27',))))
        with patch('day28_delivery.recover_with_lease', side_effect=validate):
            with ThreadPoolExecutor(max_workers=2) as pool:
                delivery = pool.submit(self.deliver)
                self.assertTrue(entered.wait(5))
                update = pool.submit(revoke)
                self.assertTrue(updating.wait(5))
                self.assertFalse(update.done())
                proceed.set()
                self.assertTrue(delivery.result(5).released)
                update.result(5)
        self.assertDenied(self.deliver())

    def test_restart_and_downstream_use_are_outside_boundary(self):
        delivered = self.deliver()
        self.boundary.update(replace(self.state, authority=Authority(5, ('lease:27',))))
        self.assertIn('23 minutes', delivered.text)
        self.boundary = DeliveryBoundary(self.state)
        self.assertDenied(self.deliver())
        # Re-admitting the same work after restart is deliberately possible.
        self.assertTrue(self.deliver(self.accept()).released)
