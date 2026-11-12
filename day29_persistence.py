"""Durable claims for offline simulated dispatch; never a delivery receipt."""
from contextlib import closing
from dataclasses import asdict, replace
import hashlib
import json
import sqlite3
from threading import Lock

from day24_recovery import Outcome
from day28_delivery import DeliveryBoundary

POLICY = 'day29-durable-claim-v1'
SCHEMA = 'CREATE TABLE claims (operation_id TEXT PRIMARY KEY NOT NULL, binding TEXT NOT NULL)'


def deny(reason):
    return Outcome(False, None, reason, False, None, (), None, (), POLICY)


class ReplayLedger:
    """Trusted local database. Provision once; open never recreates missing storage.

    Removing, rolling back or tampering with the database defeats the guarantee.
    Each attempt uses a separate connection and FULL synchronous rollback journal.
    """
    @staticmethod
    def provision(path):
        # Exclusive creation prevents silently replacing an existing ledger.
        with open(path, 'xb'):
            pass
        with closing(sqlite3.connect(path)) as db, db:
            db.execute(SCHEMA)
            db.execute('PRAGMA user_version=29')

    def __init__(self, path):
        self.path = str(path)

    def claim(self, operation_id, binding):
        db = None
        try:
            from pathlib import Path
            uri = Path(self.path).resolve().as_uri() + '?mode=rw'
            db = sqlite3.connect(uri, uri=True, timeout=2)
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            schema = db.execute("SELECT sql FROM sqlite_master WHERE name='claims'").fetchone()
            if (db.execute('PRAGMA user_version').fetchone() != (29,)
                    or schema != (SCHEMA,)
                    or db.execute('PRAGMA quick_check').fetchall() != [('ok',)]):
                return 'ledger_invalid'
            row = db.execute('SELECT binding FROM claims WHERE operation_id=?',
                             (operation_id,)).fetchone()
            if row is not None:
                return 'consumed_operation_id' if row == (binding,) else 'operation_binding_mismatch'
            db.execute('INSERT INTO claims VALUES (?, ?)', (operation_id, binding))
            db.commit()
            return None
        except (sqlite3.Error, OSError, ValueError):
            # Commit ambiguity must not release text. Retry may find a committed claim.
            return 'ledger_unavailable'
        finally:
            if db is not None:
                db.close()


class PersistentBoundary:
    """Re-admit after restart with the SAME trusted operation ID and fresh state.

    Pending receipts stay in memory. No candidate or rendered text is persisted.
    Updates and the validation/claim decision share one process-local lock.
    Independent workers must receive current trusted authorization themselves.
    """
    def __init__(self, state, ledger):
        self._boundary = DeliveryBoundary(state)
        self._ledger = ledger
        self._lock = Lock()
        self._operations = {}

    def prepare(self):
        with self._lock:
            return self._boundary.prepare()

    def update(self, state):
        with self._lock:
            self._boundary.update(state)

    def accept(self, operation_id, ticket, candidate, *, original, now):
        with self._lock:
            if type(operation_id) is not str or not 1 <= len(operation_id) <= 128:
                return None
            receipt = self._boundary.accept(ticket, candidate, original=original, now=now)
            if receipt is not None:
                # Includes recipient/task, exact records, pins, lease and authority.
                # Exclude only the snapshot clock so a restart can use fresh time.
                state = asdict(ticket.state)
                state['snapshot'].pop('now')
                binding = hashlib.sha256(json.dumps(state, sort_keys=True,
                                                    separators=(',', ':')).encode()).hexdigest()
                self._operations[receipt.delivery_id] = (operation_id, binding)
            return receipt

    def deliver(self, delivery_id, *, recipient, task, now):
        with self._lock:
            result = self._boundary.deliver(delivery_id, recipient=recipient, task=task, now=now)
            if not result.released:
                return replace(result, policy=POLICY)
            operation_id, binding = self._operations.pop(delivery_id)
            reason = self._ledger.claim(operation_id, binding)
            if reason:
                return deny(reason)
            return replace(result, policy=POLICY)
