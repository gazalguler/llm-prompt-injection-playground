"""SQLite receiver for Day 30 claims; effects are local database rows only."""
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3

from day30_outbox import Claim

SCHEMAS = (
    'CREATE TABLE receipts (operation_id TEXT PRIMARY KEY NOT NULL, recipient TEXT NOT NULL, '
    'task TEXT NOT NULL, payload TEXT NOT NULL)',
    'CREATE TABLE effects (operation_id TEXT PRIMARY KEY NOT NULL REFERENCES receipts(operation_id), '
    'payload TEXT NOT NULL)',
)


class Receiver:
    """Trusted caller supplies claims and authenticated recipient/task identity.

    Provision once and retain the database across retries. A successful receive
    means the local transaction committed, including for an identical duplicate.
    None means rejection or uncertainty; it must never authorize an outbox ack.
    """
    @staticmethod
    def provision(path):
        with open(path, 'xb'):
            pass
        with closing(sqlite3.connect(path)) as db, db:
            for schema in SCHEMAS:
                db.execute(schema)
            db.execute('PRAGMA user_version=31')

    def __init__(self, path, *, recipient, task):
        self.path = str(path)
        self.recipient = recipient
        self.task = task

    @contextmanager
    def _transaction(self):
        uri = Path(self.path).resolve().as_uri() + '?mode=rw'
        with closing(sqlite3.connect(uri, uri=True, timeout=0.2)) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            try:
                if (db.execute('PRAGMA user_version').fetchone() != (31,)
                        or any(db.execute('SELECT sql FROM sqlite_master WHERE name=?', (name,)).fetchone()
                               != (schema,) for name, schema in zip(('receipts', 'effects'), SCHEMAS))
                        or db.execute('PRAGMA quick_check').fetchall() != [('ok',)]
                        or db.execute('PRAGMA foreign_key_check').fetchall()):
                    raise sqlite3.DatabaseError('invalid receiver')
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def receive(self, claim, *, recipient, task):
        """Bind a global operation key to exact recipient, task and payload bytes.

        Returns 'applied', 'duplicate', or None. Tokens intentionally do not form
        part of the binding: each outbox retry has a fresh fencing token.
        """
        if (type(claim) is not Claim or type(claim.operation_id) is not str
                or not 1 <= len(claim.operation_id) <= 128
                or type(recipient) is not str or type(task) is not str
                or recipient != self.recipient or task != self.task
                or not getattr(claim.outcome, 'released', False)
                or type(getattr(claim.outcome, 'text', None)) is not str):
            return None
        binding = (recipient, task, claim.outcome.text)
        try:
            with self._transaction() as db:
                row = db.execute('SELECT recipient, task, payload FROM receipts WHERE operation_id=?',
                                 (claim.operation_id,)).fetchone()
                if row is not None:
                    effect = db.execute('SELECT payload FROM effects WHERE operation_id=?',
                                        (claim.operation_id,)).fetchone()
                    result = 'duplicate' if row == binding and effect == (binding[2],) else None
                else:
                    db.execute('INSERT INTO receipts VALUES (?, ?, ?, ?)', (claim.operation_id, *binding))
                    db.execute('INSERT INTO effects VALUES (?, ?)', (claim.operation_id, binding[2]))
                    result = 'applied'
            return result
        except (sqlite3.Error, OSError, ValueError):
            return None


def dispatch(outbox, receiver, operation_id, *, recipient, task, now):
    """Simulate claim -> receiver commit -> ack using the existing Day 30 outbox."""
    claim = outbox.claim(operation_id, recipient=recipient, task=task, now=now)
    if claim is None:
        return False
    if receiver.receive(claim, recipient=recipient, task=task) is None:
        return False
    return outbox.ack(claim, now=now)
