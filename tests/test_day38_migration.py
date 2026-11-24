"""Offline migration of synthetic predecessor schemas for the outbox and receiver."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import day38_migration as migration
from day24_recovery import TASK
from day29_persistence import ReplayLedger
from day30_outbox import Outbox
from day31_receiver import Receiver
from tests.test_day33_recovery import ORIGINAL, RECIPIENT, make_workers


CRASH_WORKER = """
import os
import sys
from unittest.mock import patch

import day38_migration as migration

migrate, path, edge = sys.argv[1:]
validate = migration._validate

def interrupt(db, schemas):
    validate(db, schemas)
    version, = db.execute('PRAGMA user_version').fetchone()
    if version in (30, 31) and edge == 'before':
        os._exit(38)

with patch.object(migration, '_validate', interrupt):
    getattr(migration, migrate)(path)
if edge == 'after':
    os._exit(38)
raise SystemExit('worker missed interruption point')
"""


class MigrationTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.sender = Path(directory) / 'sender.sqlite'
        self.receiver = Path(directory) / 'receiver.sqlite'
        Outbox.provision(self.sender)
        Receiver.provision(self.receiver)
        _, self.box, self.sink = make_workers(self.sender, self.receiver)
        for key in ('pending', 'leased', 'done'):
            self.assertTrue(self.box.enqueue(key, self.box.prepare(), 'discarded',
                                             original=ORIGINAL, now=1000))
        self.leased = self.claim(self.box, 'leased', now=1001)
        self.done = self.claim(self.box, 'done', now=1001)
        for claim in (self.leased, self.done):
            self.assertEqual(self.receive(self.sink, claim), 'applied')
        self.assertTrue(self.box.ack(self.done, now=1001))
        self.targets = (
            (self.sender, migration.migrate_outbox, ('outbox',),
             'ALTER TABLE outbox RENAME COLUMN text TO rendered_text', 1),
            (self.receiver, migration.migrate_receiver, ('receipts', 'effects'),
             'ALTER TABLE effects RENAME COLUMN payload TO effect_payload', 2),
        )

    def execute(self, path, *statements):
        with closing(sqlite3.connect(path)) as db, db:
            for statement in statements:
                db.execute(statement)

    def snapshot(self, path, tables):
        with closing(sqlite3.connect(path)) as db:
            version, = db.execute('PRAGMA user_version').fetchone()
            schema = db.execute('SELECT type, name, sql FROM sqlite_master ORDER BY name').fetchall()
            rows = [db.execute(f'SELECT rowid, * FROM {table} ORDER BY rowid').fetchall()
                    for table in tables]
        return version, schema, rows

    def synthetic_fixture(self, target):
        path, _, _, rename, source_version = target
        self.execute(path, 'BEGIN IMMEDIATE', rename, f'PRAGMA user_version={source_version}')

    def claim(self, box, key, *, now, recipient=RECIPIENT):
        return box.claim(key, recipient=recipient, task=TASK, now=now)

    def receive(self, sink, claim, *, recipient=RECIPIENT):
        return sink.receive(claim, recipient=recipient, task=TASK)

    def test_migrates_back_to_exact_current_schema_and_rows(self):
        for target in self.targets:
            path, migrate, tables, _, _ = target
            with self.subTest(path=path.name):
                expected = self.snapshot(path, tables)
                self.synthetic_fixture(target)
                self.assertTrue(migrate(path))
                self.assertEqual(self.snapshot(path, tables), expected)

    def test_repeated_migration_validates_and_preserves_records(self):
        for target in self.targets:
            path, migrate, tables, _, _ = target
            with self.subTest(path=path.name):
                self.synthetic_fixture(target)
                self.assertTrue(migrate(path))
                expected = self.snapshot(path, tables)
                self.assertFalse(migrate(path))
                self.assertEqual(self.snapshot(path, tables), expected)

    def test_reopened_workers_preserve_authority_and_deduplication(self):
        for target in self.targets:
            path, migrate, *_ = target
            self.synthetic_fixture(target)
            self.assertTrue(migrate(path))
        _, box, sink = make_workers(self.sender, self.receiver)
        self.assertIsNone(self.claim(box, 'done', now=1006))
        self.assertFalse(box.ack(self.done, now=1002))
        self.assertIsNone(self.claim(box, 'pending', now=1002, recipient='owner:other'))
        self.assertIsNone(self.claim(box, 'leased', now=1005))
        retry = self.claim(box, 'leased', now=1006)
        self.assertIsNotNone(retry)
        self.assertNotEqual(retry.token, self.leased.token)
        self.assertFalse(box.ack(self.leased, now=1006))
        self.assertIsNone(self.receive(sink, retry, recipient='owner:other'))
        conflict = replace(retry, outcome=replace(retry.outcome, text='different payload'))
        self.assertIsNone(self.receive(sink, conflict))
        self.assertEqual(self.receive(sink, retry), 'duplicate')
        self.assertTrue(box.ack(retry, now=1006))
        pending = self.claim(box, 'pending', now=1006)
        self.assertIsNotNone(pending)
        self.assertEqual(self.receive(sink, pending), 'applied')
        self.assertTrue(box.ack(pending, now=1006))
        _, _, (_, effects) = self.snapshot(self.receiver, ('receipts', 'effects'))
        self.assertEqual(len(effects), 3)

    def test_normal_workers_fail_closed_before_explicit_migration(self):
        for target in self.targets:
            self.synthetic_fixture(target)
        sender_before = self.snapshot(self.sender, ('outbox',))
        receiver_before = self.snapshot(self.receiver, ('receipts', 'effects'))
        self.assertIsNone(self.claim(self.box, 'pending', now=1002))
        self.assertIsNone(self.receive(self.sink, self.leased))
        self.assertEqual(self.snapshot(self.sender, ('outbox',)), sender_before)
        self.assertEqual(self.snapshot(self.receiver, ('receipts', 'effects')), receiver_before)

    def test_rejects_malformed_source_schema(self):
        for target in self.targets:
            path, migrate, tables, _, _ = target
            with self.subTest(path=path.name):
                self.synthetic_fixture(target)
                self.execute(path, f'ALTER TABLE {tables[-1]} ADD COLUMN unexpected TEXT')
                expected = self.snapshot(path, tables)
                with self.assertRaisesRegex(sqlite3.DatabaseError, 'unexpected migration schema'):
                    migrate(path)
                self.assertEqual(self.snapshot(path, tables), expected)

    def test_rejects_extra_schema_objects_on_current_version(self):
        self.execute(self.sender, 'CREATE INDEX unexpected ON outbox(status)')
        expected = self.snapshot(self.sender, ('outbox',))
        with self.assertRaisesRegex(sqlite3.DatabaseError, 'unexpected migration schema'):
            migration.migrate_outbox(self.sender)
        self.assertEqual(self.snapshot(self.sender, ('outbox',)), expected)

    def test_rejects_receiver_foreign_key_violation(self):
        self.synthetic_fixture(self.targets[1])
        self.execute(self.receiver, "DELETE FROM receipts WHERE operation_id='leased'")
        expected = self.snapshot(self.receiver, ('receipts', 'effects'))
        with self.assertRaisesRegex(sqlite3.DatabaseError, 'foreign key'):
            migration.migrate_receiver(self.receiver)
        self.assertEqual(self.snapshot(self.receiver, ('receipts', 'effects')), expected)

    def test_rejects_unsupported_versions_and_other_store(self):
        for target in self.targets:
            path, migrate, tables, _, _ = target
            for version in (0, 29, 999):
                with self.subTest(path=path.name, version=version):
                    self.execute(path, f'PRAGMA user_version={version}')
                    expected = self.snapshot(path, tables)
                    with self.assertRaisesRegex(sqlite3.DatabaseError, 'unsupported migration version'):
                        migrate(path)
                    self.assertEqual(self.snapshot(path, tables), expected)
        ledger = self.sender.with_name('ledger.sqlite')
        ReplayLedger.provision(ledger)
        store = ReplayLedger(ledger)
        self.assertIsNone(store.claim('claimed', 'original binding'))
        for migrate in (migration.migrate_outbox, migration.migrate_receiver):
            with self.assertRaisesRegex(sqlite3.DatabaseError, 'unsupported migration version'):
                migrate(ledger)
        self.assertEqual(store.claim('claimed', 'original binding'), 'consumed_operation_id')
        self.assertEqual(store.claim('claimed', 'different binding'), 'operation_binding_mismatch')

    def test_missing_database_is_not_created(self):
        path = self.sender.with_name('missing.sqlite')
        with self.assertRaises(sqlite3.OperationalError):
            migration.migrate_outbox(path)
        self.assertFalse(path.exists())

    def test_rolls_back_when_post_rename_validation_fails(self):
        for target in self.targets:
            path, migrate, tables, _, _ = target
            with self.subTest(path=path.name):
                self.synthetic_fixture(target)
                expected = self.snapshot(path, tables)
                with patch.object(migration, '_validate', side_effect=(
                        None, sqlite3.DatabaseError('simulated target validation failure'))):
                    with self.assertRaisesRegex(sqlite3.DatabaseError, 'target validation failure'):
                        migrate(path)
                self.assertEqual(self.snapshot(path, tables), expected)
                self.assertTrue(migrate(path))

    def test_writer_lock_leaves_source_intact(self):
        self.synthetic_fixture(self.targets[0])
        expected = self.snapshot(self.sender, ('outbox',))
        with closing(sqlite3.connect(self.sender)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):
                migration.migrate_outbox(self.sender)
        self.assertEqual(self.snapshot(self.sender, ('outbox',)), expected)
        self.assertTrue(migration.migrate_outbox(self.sender))

    def test_rejects_wal_without_changing_journal_mode_or_rows(self):
        self.synthetic_fixture(self.targets[0])
        with closing(sqlite3.connect(self.sender)) as db:
            self.assertEqual(db.execute('PRAGMA journal_mode=WAL').fetchone(), ('wal',))
        expected = self.snapshot(self.sender, ('outbox',))
        with self.assertRaisesRegex(sqlite3.DatabaseError, 'requires DELETE journal'):
            migration.migrate_outbox(self.sender)
        self.assertEqual(self.snapshot(self.sender, ('outbox',)), expected)
        with closing(sqlite3.connect(self.sender)) as db:
            self.assertEqual(db.execute('PRAGMA journal_mode').fetchone(), ('wal',))

    def test_process_exit_before_and_after_commit(self):
        for target in self.targets:
            path, migrate, tables, _, _ = target
            current = self.snapshot(path, tables)
            self.synthetic_fixture(target)
            source = self.snapshot(path, tables)
            for edge, expected in (('before', source), ('after', current)):
                with self.subTest(path=path.name, edge=edge):
                    worker = subprocess.run(
                        [sys.executable, '-B', '-S', '-c', CRASH_WORKER,
                         migrate.__name__, str(path), edge],
                        cwd=Path(__file__).resolve().parents[1],
                        capture_output=True, text=True, timeout=15,
                    )
                    self.assertEqual(worker.returncode, 38, worker.stderr)
                    self.assertEqual(self.snapshot(path, tables), expected)
            self.assertFalse(migrate(path))
