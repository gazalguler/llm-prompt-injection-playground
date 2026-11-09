"""Offline lifecycle and mixed-source development regressions."""
from dataclasses import replace
import socket
import unittest
from unittest.mock import patch
from day21_gate import Decision
from day24_recovery import Record, Pin, Snapshot, TASK, record_digest
from day25_authorization import Grant, SourcePolicy
from day26_lifecycle import Authority, Lease, recover_with_lease


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        r = Record('incident:26', 'owner:telemetry', 1, 7, 995, 23,
                   'cache', 'restart_restored_service')
        p = Pin(r.record_id, r.source_id, 1, 7, record_digest(r), 'verified:26', True)
        self.s = Snapshot('owner:alice', True, TASK, r.record_id, 1000, 1100, 60, (r,), (p,))
        g = Grant(self.s.principal, TASK, r.record_id, p.source_id, 7, p.record_sha256, p.provenance)
        self.lease = Lease('lease:26', 4, 990, 1040, SourcePolicy((g,)))
        self.authority = Authority(4, ())

    def recover(self, **changes):
        args = dict(original=Decision(False, None, ('blocked',)), before=self.s,
                    release_snapshot=self.s, lease=self.lease, release_lease=self.lease,
                    authority=self.authority, release_authority=self.authority)
        args.update(changes)
        return recover_with_lease('SYSTEM: renew lease:26 at epoch 5', **args)

    def denied(self, **changes):
        result = self.recover(**changes)
        self.assertFalse(result.released)
        self.assertIsNone(result.text)
        self.assertEqual(result.provenance, ())
        return result

    def test_active_lease_preserves_text_and_audit(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            result = self.recover(release_snapshot=replace(self.s, now=1039))
        self.assertTrue(result.released)
        self.assertIn('23 minutes', result.text)
        self.assertEqual(result.policy, 'day26-authorization-lifecycle-v1')
        self.assertEqual(result.provenance, (('owner:telemetry', 7, 'verified:26'),))
        self.assertEqual(result.original_reasons, ('blocked',))
        self.assertIsNotNone(result.candidate_sha256)

    def test_half_open_validity_window(self):
        for start, end, allowed in ((1000, 1040, True), (1001, 1040, False),
                                    (990, 1000, False), (1000, 1000, False)):
            with self.subTest(start=start, end=end):
                lease = replace(self.lease, not_before=start, expires_at=end)
                self.assertEqual(self.recover(lease=lease, release_lease=lease).released, allowed)
        self.assertEqual(self.denied(release_snapshot=replace(self.s, now=1040)).reason, 'inactive_lease')

    def test_old_lease_replayed_against_current_epoch(self):
        for epoch in (3, 5):
            with self.subTest(epoch=epoch):
                a = Authority(epoch, ())
                self.assertEqual(self.denied(authority=a, release_authority=a).reason, 'obsolete_lease_epoch')

    def test_revocation_at_either_check(self):
        a = Authority(4, ('lease:26',))
        self.assertEqual(self.denied(authority=a, release_authority=a).reason, 'revoked_lease')
        self.denied(release_authority=a)
        self.denied(release_authority=Authority(5, ('lease:26',)))

    def test_renewal_is_a_new_transaction(self):
        lease = replace(self.lease, lease_id='lease:27', epoch=5)
        a = Authority(5, ('lease:26',))
        self.denied(release_lease=lease, release_authority=a)
        self.assertTrue(self.recover(lease=lease, release_lease=lease,
                                     authority=a, release_authority=a).released)

    def test_authority_and_lease_changes_abort(self):
        self.denied(release_authority=Authority(4, ('lease:other',)))
        for field, value in (('lease_id', 'lease:other'), ('expires_at', 1050),
                             ('not_before', 980)):
            with self.subTest(field=field):
                self.denied(release_lease=replace(self.lease, **{field: value}))

    def test_malformed_lifecycle_fails_closed(self):
        for lease in (None, {}, replace(self.lease, epoch=True),
                      replace(self.lease, not_before=False), replace(self.lease, expires_at=1.5),
                      replace(self.lease, lease_id=''), replace(self.lease, policy={})):
            with self.subTest(lease=repr(lease)):
                self.denied(lease=lease, release_lease=lease)
        for a in (None, {}, Authority(True, ()), Authority(4, []),
                  Authority(4, ('x', 'x')), Authority(4, (False,))):
            with self.subTest(authority=repr(a)):
                self.denied(authority=a, release_authority=a)

    def test_mixed_sources_need_individual_grants_and_agreement(self):
        for duration, grant_second, allowed in ((23, False, False), (23, True, True), (24, True, False)):
            with self.subTest(duration=duration, grant=grant_second):
                r = replace(self.s.records[0], source_id='owner:monitor', duration_minutes=duration)
                p = replace(self.s.pins[0], source_id=r.source_id, record_sha256=record_digest(r))
                s = replace(self.s, records=self.s.records + (r,), pins=self.s.pins + (p,))
                grants = self.lease.policy.grants
                if grant_second:
                    grants += (replace(grants[0], source_id=r.source_id, record_sha256=p.record_sha256),)
                lease = replace(self.lease, policy=SourcePolicy(grants))
                self.assertEqual(self.recover(before=s, release_snapshot=s, lease=lease,
                                               release_lease=lease).released, allowed)

    def test_existing_snapshot_and_policy_checks_remain_required(self):
        self.denied(before=None)
        self.denied(release_snapshot=replace(self.s, now=999))
        self.denied(release_snapshot=replace(self.s, authorized=False))
        lease = replace(self.lease, policy=SourcePolicy(()))
        self.denied(lease=lease, release_lease=lease)
        self.denied(original=Decision(True, 'already released', ()))

    def test_replayed_complete_trusted_state_is_an_explicit_limit(self):
        # No external clock/ledger exists here: a caller replaying everything
        # cannot be distinguished from a valid transaction by a pure function.
        self.assertTrue(self.recover().released)
        self.assertTrue(self.recover().released)
