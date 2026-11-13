"""Offline transactional outbox. Trusted state, clock and local storage only."""
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
import sqlite3
from threading import Lock
from uuid import uuid4

from day21_gate import Decision
from day28_delivery import DeliveryBoundary

SCHEMA = ('CREATE TABLE outbox (operation_id TEXT PRIMARY KEY NOT NULL, '
          'context TEXT NOT NULL, text TEXT NOT NULL, accepted INTEGER NOT NULL, '
          'status TEXT NOT NULL, token TEXT, until_time INTEGER NOT NULL, '
          'attempts INTEGER NOT NULL, last_time INTEGER NOT NULL)')
POLICY = 'day30-offline-outbox-v1'


def context(state):
    value = asdict(state)
    value['snapshot'].pop('now')
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


@dataclass(frozen=True)
class Claim:
    operation_id: str
    token: str
    outcome: object


class Outbox:
    """Provision separately; opening missing or incompatible storage fails closed.

    claim() is the simulated send boundary, ack() records receiver acknowledgement.
    An expired claim can be retried; receivers must deduplicate operation_id.
    Each worker must independently obtain fresh authority before every claim.
    """
    @staticmethod
    def provision(path):
        with open(path, 'xb'):
            pass
        with closing(sqlite3.connect(path)) as db, db:
            db.execute(SCHEMA)
            db.execute('PRAGMA user_version=30')

    def __init__(self, state, path):
        self._boundary = DeliveryBoundary(state)
        self._path = str(path)
        self._lock = Lock()

    @contextmanager
    def _transaction(self):
        uri = Path(self._path).resolve().as_uri() + '?mode=rw'
        with closing(sqlite3.connect(uri, uri=True, timeout=0.2)) as db:
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            try:
                if (db.execute('PRAGMA user_version').fetchone() != (30,)
                        or db.execute("SELECT sql FROM sqlite_master WHERE name='outbox'").fetchone() != (SCHEMA,)
                        or db.execute('PRAGMA quick_check').fetchall() != [('ok',)]):
                    raise sqlite3.DatabaseError('invalid outbox')
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def prepare(self):
        with self._lock:
            return self._boundary.prepare()

    def update(self, state):
        with self._lock:
            self._boundary.update(state)

    def enqueue(self, operation_id, ticket, candidate, *, original, now):
        """Persist the trusted rendered intent and full binding together; no candidate."""
        with self._lock:
            if type(operation_id) is not str or not 1 <= len(operation_id) <= 128:
                return False
            receipt = self._boundary.accept(ticket, candidate, original=original, now=now)
            if receipt is None:
                return False
            result = self._boundary.deliver(receipt.delivery_id, recipient=receipt.recipient,
                                            task=receipt.task, now=now)
            if not result.released:
                return False
            binding = context(ticket.state)
            try:
                with self._transaction() as db:
                    row = db.execute('SELECT context, text FROM outbox WHERE operation_id=?',
                                     (operation_id,)).fetchone()
                    if row is not None:
                        return row == (binding, result.text)
                    db.execute('INSERT INTO outbox VALUES (?, ?, ?, ?, ?, NULL, 0, 0, ?)',
                               (operation_id, binding, result.text, now, 'pending', now))
                return True
            except (sqlite3.Error, OSError, ValueError):
                return False

    def claim(self, operation_id, *, recipient, task, now, lease_seconds=5, max_attempts=3):
        """Return a fenced simulated handoff only after its claim commits.

        Retry configuration is fixed at this boundary: trusted caller supplies it.
        No background worker, wall-clock read or network send is hidden here.
        """
        with self._lock:
            if (type(operation_id) is not str or type(now) is not int
                    or type(lease_seconds) is not int or not 1 <= lease_seconds <= 60
                    or type(max_attempts) is not int or not 1 <= max_attempts <= 10):
                return None
            ticket = self._boundary.prepare()
            validator = DeliveryBoundary(ticket.state)
            receipt = validator.accept(validator.prepare(), '',
                                       original=Decision(False, None, ('blocked',)), now=now)
            if receipt is None:
                return None
            result = validator.deliver(receipt.delivery_id, recipient=recipient, task=task, now=now)
            if not result.released:
                return None
            try:
                with self._transaction() as db:
                    row = db.execute('SELECT context, text, accepted, status, until_time, attempts, last_time '
                                     'FROM outbox WHERE operation_id=?', (operation_id,)).fetchone()
                    if row is None:
                        return None
                    binding, text, accepted, status, until, attempts, last = row
                    if (binding != context(ticket.state) or text != result.text or now < max(accepted, last)
                            or status == 'done' or (status == 'leased' and now < until)
                            or attempts >= max_attempts):
                        return None
                    token = uuid4().hex
                    db.execute('UPDATE outbox SET status=?, token=?, until_time=?, attempts=?, last_time=? '
                               'WHERE operation_id=?', ('leased', token, now + lease_seconds,
                                                        attempts + 1, now, operation_id))
                # Audit hashes describe this fresh validation, not the discarded candidate.
                return Claim(operation_id, token, replace(result, policy=POLICY))
            except (sqlite3.Error, OSError, ValueError):
                return None

    def ack(self, claim, *, now):
        """A stale worker cannot acknowledge a later worker's lease."""
        if type(claim) is not Claim or type(now) is not int:
            return False
        with self._lock:
            try:
                with self._transaction() as db:
                    cursor = db.execute('UPDATE outbox SET status=?, last_time=? WHERE operation_id=? '
                                        'AND status=? AND token=? AND last_time<=? AND until_time>?',
                                        ('done', now, claim.operation_id, 'leased', claim.token, now, now))
                    changed = cursor.rowcount == 1
                return changed
            except (sqlite3.Error, OSError, ValueError):
                return False
