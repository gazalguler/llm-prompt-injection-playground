"""Compare the offline delivery workflow with an independent in-memory model."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict, dataclass, replace
from itertools import product
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest
from unittest.mock import patch

from day21_gate import Decision
from day24_recovery import TASK, record_digest
from day25_authorization import SourcePolicy
from day26_lifecycle import Authority
from day30_outbox import Outbox
from day31_receiver import Receiver
from day32_delivery import Fault, OfflineTransport, deliver
from tests import test_day27_release as fixtures


KEY = 'job:34'
RECIPIENT = 'owner:alice'
ORIGINAL = Decision(False, None, ('blocked',))
ATTEMPTS = {
    'normal': Fault.NONE,
    'outage': Fault.TRANSPORT_UNAVAILABLE,
    'lost_ack': Fault.LOST_ACK,
    'duplicate': Fault.DUPLICATE_MESSAGE,
    'changed_frame': Fault.NONE,
}


def payload(minutes):
    return (f'System-rendered incident summary: The application was unavailable for '
            f'{minutes} minutes, and service was restored by restarting the cache.')


class ChangedFrameTransport(OfflineTransport):
    def frames(self, message):
        return (message, replace(message, payload=payload(24)))


@dataclass
class RecoveryModel:
    """One operation, five-second leases, three claims, and a separate effect."""

    access: str = 'original'
    status: str | None = None
    accepted: int = 0
    attempts: int = 0
    deadline: int = 0
    last_time: int = 0
    effect: str | None = None

    def enqueue(self, now):
        if self.access != 'original' or not 1000 <= now < 1040:
            return False
        if self.status is None:
            self.status = 'pending'
            self.accepted = self.last_time = now
        return True

    def claim(self, now):
        if self.access != 'original' or not 1000 <= now < 1040:
            return None
        eligible_at = {'pending': self.last_time, 'leased': self.deadline}.get(self.status)
        if eligible_at is None or now < eligible_at or self.attempts == 3:
            return None
        self.status = 'leased'
        self.deadline = now + 5
        self.last_time = now
        self.attempts += 1
        return self.attempts

    def acknowledge(self, generation, now):
        if (self.status, generation) != ('leased', self.attempts):
            return False
        if not self.last_time <= now < self.deadline:
            return False
        self.status = 'done'
        self.last_time = now
        return True

    def receive(self, text):
        if self.effect is not None:
            return 'duplicate' if text == self.effect else None
        self.effect = text
        return 'applied'

    def attempt(self, mode, now):
        generation = self.claim(now)
        if generation is None:
            return ('claim_unavailable', ())
        if mode == 'outage':
            return ('transport_unavailable', ())
        if mode == 'changed_frame':
            return ('invalid_message', ())
        results = (self.receive(payload(23)),)
        if mode == 'duplicate':
            results += (self.receive(payload(23)),)
        if mode == 'lost_ack':
            return ('ack_lost', results)
        self.acknowledge(generation, now)
        return ('done', results)


class RecoveryModelTests(unittest.TestCase):
    def provision(self, directory):
        self.sender_path = Path(directory) / 'sender.sqlite'
        self.receiver_path = Path(directory) / 'receiver.sqlite'
        Outbox.provision(self.sender_path)
        Receiver.provision(self.receiver_path)

        fixture = fixtures.ReleaseQueueTests()
        fixture.setUp()
        original = fixture.state
        record = replace(original.snapshot.records[0], revision=8, duration_minutes=24)
        pin = replace(original.snapshot.pins[0], revision=8, record_sha256=record_digest(record))
        grant = replace(original.lease.policy.grants[0], revision=8, record_sha256=pin.record_sha256)
        self.states = {
            'original': original,
            'revoked': replace(original, authority=Authority(5, ('lease:27',))),
            'changed': replace(original,
                               snapshot=replace(original.snapshot, records=(record,), pins=(pin,)),
                               lease=replace(original.lease, policy=SourcePolicy((grant,)))),
        }
        binding = asdict(original)
        del binding['snapshot']['now']
        self.binding = json.dumps(binding, sort_keys=True, separators=(',', ':'))
        self.model = RecoveryModel()
        self.claims = {}
        self.restart()

    def restart(self):
        self.box = Outbox(self.states[self.model.access], self.sender_path)
        self.receiver = Receiver(self.receiver_path, recipient=RECIPIENT, task=TASK)
        self.assert_snapshot()

    def assert_snapshot(self):
        model = self.model
        claim = self.claims.get(model.attempts)
        sender = [] if model.status is None else [
            (KEY, self.binding, payload(23), model.accepted, model.status,
             claim.token if claim else None, model.deadline, model.attempts, model.last_time)
        ]
        receipts = [] if model.effect is None else [(KEY, RECIPIENT, TASK, model.effect)]
        effects = [] if model.effect is None else [(KEY, model.effect)]
        with closing(sqlite3.connect(self.sender_path)) as db:
            self.assertEqual(db.execute('SELECT * FROM outbox').fetchall(), sender)
        with closing(sqlite3.connect(self.receiver_path)) as db:
            self.assertEqual(db.execute('SELECT * FROM receipts').fetchall(), receipts)
            self.assertEqual(db.execute('SELECT * FROM effects').fetchall(), effects)

    def enqueue(self, now=1000):
        expected = self.model.enqueue(now)
        self.assertEqual(self.box.enqueue(KEY, self.box.prepare(), 'discarded-candidate',
                                          original=ORIGINAL, now=now), expected)
        self.assert_snapshot()

    def observe_claim(self, generation, claim):
        if generation is None:
            self.assertIsNone(claim)
            return
        self.assertIsNotNone(claim)
        self.assertEqual(claim.operation_id, KEY)
        self.assertTrue(claim.outcome.released)
        self.assertEqual(claim.outcome.text, payload(23))
        self.assertTrue(claim.token)
        self.assertNotIn(claim.token, {previous.token for previous in self.claims.values()})
        self.claims[generation] = claim

    def claim(self, now):
        expected = self.model.claim(now)
        self.observe_claim(expected, self.box.claim(KEY, recipient=RECIPIENT, task=TASK, now=now))
        self.assert_snapshot()

    def acknowledge(self, generation, now, *, wrong_token=False):
        claim = self.claims[generation]
        if wrong_token:
            claim = replace(claim, token='wrong-token')
        expected = self.model.acknowledge(None if wrong_token else generation, now)
        self.assertEqual(self.box.ack(claim, now=now), expected)
        self.assert_snapshot()

    def receive(self, generation, minutes):
        claim = self.claims[generation]
        text = payload(minutes)
        if minutes != 23:
            claim = replace(claim, outcome=replace(claim.outcome, text=text))
        self.assertEqual(self.receiver.receive(claim, recipient=RECIPIENT, task=TASK),
                         self.model.receive(text))
        self.assert_snapshot()

    def update(self, access):
        self.model.access = access
        self.box.update(self.states[access])
        self.assert_snapshot()

    def attempt(self, mode, now):
        transport_type = ChangedFrameTransport if mode == 'changed_frame' else OfflineTransport
        transport = transport_type(ATTEMPTS[mode])
        claims = []
        original_claim = self.box.claim

        def capture(*args, **kwargs):
            claim = original_claim(*args, **kwargs)
            claims.append(claim)
            return claim

        before = self.model.attempts
        expected = self.model.attempt(mode, now)
        with patch.object(self.box, 'claim', side_effect=capture):
            result = deliver(self.box, self.receiver, KEY, recipient=RECIPIENT,
                             task=TASK, now=now, transport=transport)
        self.assertEqual((result.status, result.receiver_results), expected)
        [claim] = claims
        generation = self.model.attempts if self.model.attempts != before else None
        self.observe_claim(generation, claim)
        self.assert_snapshot()

    def test_all_three_attempt_fault_sequences(self):
        for sequence in product(ATTEMPTS, repeat=3):
            with self.subTest(sequence=sequence), TemporaryDirectory() as directory:
                self.provision(directory)
                self.attempt('normal', 1000)
                self.enqueue()
                for now, mode in zip((1001, 1006, 1011), sequence):
                    self.attempt(mode, now)
                    self.restart()
                    self.attempt('normal', now + 4)
                self.attempt('normal', 1016)

    def test_acknowledgement_boundaries_and_receiver_binding(self):
        with TemporaryDirectory() as directory:
            self.provision(directory)
            self.enqueue(1001)
            self.enqueue(1002)
            self.claim(1000)
            self.claim(1002)
            self.receive(1, 23)
            self.acknowledge(1, 1001)
            self.acknowledge(1, 1003, wrong_token=True)
            self.acknowledge(1, 1007)
            self.restart()
            self.claim(1007)
            self.acknowledge(1, 1007)
            self.receive(2, 24)
            self.receive(2, 23)
            self.acknowledge(2, 1011)
            self.acknowledge(2, 1011)
            self.claim(1012)

    def test_revocation_and_authorized_payload_change_across_restart(self):
        with TemporaryDirectory() as directory:
            self.provision(directory)
            self.enqueue()
            self.attempt('lost_ack', 1001)
            self.update('revoked')
            self.restart()
            self.enqueue(1006)
            self.attempt('normal', 1006)
            self.update('changed')
            self.restart()
            self.enqueue(1006)
            self.attempt('normal', 1006)
            # Show that the replacement state can claim a fresh operation.
            with TemporaryDirectory() as control:
                path = Path(control) / 'changed.sqlite'
                Outbox.provision(path)
                box = Outbox(self.states['changed'], path)
                self.assertTrue(box.enqueue(KEY, box.prepare(), '', original=ORIGINAL, now=1006))
                claim = box.claim(KEY, recipient=RECIPIENT, task=TASK, now=1006)
                self.assertIsNotNone(claim)
                self.assertEqual(claim.outcome.text, payload(24))
            self.assert_snapshot()

    def test_two_workers_contend_for_one_expired_lease(self):
        for first_mode in ('outage', 'lost_ack'):
            with self.subTest(first_mode=first_mode), TemporaryDirectory() as directory:
                self.provision(directory)
                self.enqueue()
                self.attempt(first_mode, 1001)
                self.restart()
                ready = Barrier(2)

                def retry():
                    worker = Outbox(self.states['original'], self.sender_path)
                    ready.wait(timeout=5)
                    return worker.claim(KEY, recipient=RECIPIENT, task=TASK, now=1006)

                expected = self.model.claim(1006)
                self.assertIsNone(self.model.claim(1006))
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(retry) for _ in range(2)]
                    results = [future.result(timeout=10) for future in futures]
                self.assertEqual(sum(claim is None for claim in results), 1)
                self.observe_claim(expected, next(claim for claim in results if claim is not None))
                self.assert_snapshot()
                self.acknowledge(1, 1006)
                self.receive(2, 23)
                self.acknowledge(2, 1006)
