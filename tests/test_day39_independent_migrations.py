"""Exercise mixed schema versions through the offline delivery entry point."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from day24_recovery import TASK
from day30_outbox import Outbox
from day31_receiver import Receiver
from day32_delivery import Attempt, Fault, OfflineTransport, deliver
from day38_migration import migrate_outbox, migrate_receiver
from tests import test_day38_migration as day38
from tests.test_day33_recovery import KEY, RECIPIENT, enqueue, make_workers


class IndependentMigrationTests(unittest.TestCase):
    def setup_pair(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        sender, receiver = directory / 'sender.sqlite', directory / 'receiver.sqlite'
        Outbox.provision(sender)
        Receiver.provision(receiver)
        _, box, sink = make_workers(sender, receiver)
        self.assertTrue(enqueue(box))
        self.assertEqual(
            self.deliver(box, sink, 1001, transport=OfflineTransport(Fault.LOST_ACK)),
            Attempt('ack_lost', ('applied',)),
        )
        return sender, receiver

    def deliver(self, box, sink, now, **kwargs):
        return deliver(box, sink, KEY, recipient=RECIPIENT, task=TASK, now=now, **kwargs)

    def read(self, path, *queries):
        with closing(sqlite3.connect(path)) as db:
            return tuple(db.execute(query).fetchall() for query in queries)

    def sender_rows(self, sender):
        return self.read(sender, 'SELECT * FROM outbox ORDER BY operation_id')

    def receiver_rows(self, receiver):
        return self.read(receiver, 'SELECT * FROM receipts ORDER BY operation_id',
                         'SELECT * FROM effects ORDER BY operation_id')

    def downgrade(self, path, rename, version):
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute(rename)
            db.execute(f'PRAGMA user_version={version}')

    def interrupt(self, migrate, path, edge):
        worker = subprocess.run(
            [sys.executable, '-B', '-S', '-c', day38.CRASH_WORKER,
             migrate.__name__, str(path), edge],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(worker.returncode, 38, worker.stderr)

    def test_process_exit_in_either_upgrade_order(self):
        for first in ('sender', 'receiver'):
            for edge in ('before', 'after'):
                with self.subTest(first=first, edge=edge):
                    sender, receiver = self.setup_pair()
                    sender_before = self.sender_rows(sender)
                    receiver_before = self.receiver_rows(receiver)
                    self.downgrade(sender, 'ALTER TABLE outbox RENAME COLUMN text TO rendered_text', 1)
                    self.downgrade(receiver, 'ALTER TABLE effects RENAME COLUMN payload TO effect_payload', 2)
                    upgrades = [(migrate_outbox, sender), (migrate_receiver, receiver)]
                    if first == 'receiver':
                        upgrades.reverse()
                    migrate, path = upgrades[0]
                    self.interrupt(migrate, path, edge)
                    _, box, sink = make_workers(sender, receiver)
                    if first == 'sender' and edge == 'after':
                        # The sender can reserve a retry while the receiver is on v2.
                        self.assertEqual(self.deliver(box, sink, 1006), Attempt('receiver_unconfirmed'))
                        self.assertNotEqual(self.sender_rows(sender), sender_before)
                        self.assertEqual(self.deliver(box, sink, 1007), Attempt('claim_unavailable'))
                    else:
                        self.assertEqual(self.deliver(box, sink, 1006), Attempt('claim_unavailable'))
                        self.assertEqual(self.sender_rows(sender), sender_before)
                    self.assertEqual(self.receiver_rows(receiver), receiver_before)

                    sender_at_recovery = self.sender_rows(sender)
                    self.assertIs(migrate(path), edge == 'before')
                    migrate_peer, peer = upgrades[1]
                    self.assertTrue(migrate_peer(peer))
                    for upgrade, database in upgrades:
                        self.assertFalse(upgrade(database))
                    self.assertEqual(self.sender_rows(sender), sender_at_recovery)
                    self.assertEqual(self.receiver_rows(receiver), receiver_before)
                    _, box, sink = make_workers(sender, receiver)
                    self.assertEqual(self.deliver(box, sink, 1011), Attempt('done', ('duplicate',)))
                    self.assertEqual(self.receiver_rows(receiver), receiver_before)
                    self.assertEqual(self.deliver(box, sink, 1016), Attempt('claim_unavailable'))

    def test_current_receiver_deduplicates_while_sender_uses_legacy_schema(self):
        sender, receiver = self.setup_pair()
        _, box, sink = make_workers(sender, receiver)
        claim = box.claim(KEY, recipient=RECIPIENT, task=TASK, now=1006)
        self.assertIsNotNone(claim)
        self.downgrade(sender, 'ALTER TABLE outbox RENAME COLUMN text TO rendered_text', 1)
        before = self.receiver_rows(receiver)
        self.assertIsNone(sink.receive(claim, recipient='owner:other', task=TASK))
        conflict = replace(claim, outcome=replace(claim.outcome, text='changed'))
        self.assertIsNone(sink.receive(conflict, recipient=RECIPIENT, task=TASK))
        self.assertEqual(sink.receive(claim, recipient=RECIPIENT, task=TASK), 'duplicate')
        self.assertFalse(box.ack(claim, now=1007))
        self.assertEqual(self.receiver_rows(receiver), before)
        self.assertTrue(migrate_outbox(sender))
        self.assertTrue(box.ack(claim, now=1007))

    def test_unsupported_receiver_does_not_block_sender_upgrade_or_confirm_delivery(self):
        sender, receiver = self.setup_pair()
        self.downgrade(sender, 'ALTER TABLE outbox RENAME COLUMN text TO rendered_text', 1)
        before = self.receiver_rows(receiver)
        with closing(sqlite3.connect(receiver)) as db, db:
            db.execute('PRAGMA user_version=999')
        self.assertTrue(migrate_outbox(sender))
        with self.assertRaisesRegex(sqlite3.DatabaseError, 'unsupported migration version'):
            migrate_receiver(receiver)
        _, box, sink = make_workers(sender, receiver)
        self.assertEqual(self.deliver(box, sink, 1006), Attempt('receiver_unconfirmed'))
        self.assertEqual(self.read(sender, 'SELECT status, attempts FROM outbox'), ([('leased', 2)],))
        self.assertEqual(self.read(receiver, 'PRAGMA user_version'), ([(999,)],))
        self.assertEqual(self.receiver_rows(receiver), before)

    def test_receiver_rejects_mismatched_effect_after_independent_upgrade(self):
        sender, receiver = self.setup_pair()
        with closing(sqlite3.connect(receiver)) as db, db:
            db.execute('UPDATE effects SET payload=? WHERE operation_id=?', ('changed', KEY))
        self.downgrade(receiver, 'ALTER TABLE effects RENAME COLUMN payload TO effect_payload', 2)
        before = self.receiver_rows(receiver)
        self.assertTrue(migrate_receiver(receiver))
        self.assertFalse(migrate_receiver(receiver))
        _, box, sink = make_workers(sender, receiver)
        self.assertEqual(self.deliver(box, sink, 1006), Attempt('receiver_unconfirmed'))
        self.assertEqual(self.read(sender, 'SELECT status, attempts FROM outbox'), ([('leased', 2)],))
        self.assertEqual(self.receiver_rows(receiver), before)

    def test_receiver_writer_lock_does_not_block_sender_upgrade(self):
        sender, receiver = self.setup_pair()
        self.downgrade(sender, 'ALTER TABLE outbox RENAME COLUMN text TO rendered_text', 1)
        self.downgrade(receiver, 'ALTER TABLE effects RENAME COLUMN payload TO effect_payload', 2)
        before = self.receiver_rows(receiver)
        with closing(sqlite3.connect(receiver)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            self.assertTrue(migrate_outbox(sender))
            with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                migrate_receiver(receiver)
            _, box, sink = make_workers(sender, receiver)
            self.assertEqual(self.deliver(box, sink, 1006), Attempt('receiver_unconfirmed'))
        self.assertEqual(self.receiver_rows(receiver), before)
        self.assertTrue(migrate_receiver(receiver))
        self.assertEqual(self.deliver(box, sink, 1011), Attempt('done', ('duplicate',)))
        self.assertEqual(self.receiver_rows(receiver), before)
