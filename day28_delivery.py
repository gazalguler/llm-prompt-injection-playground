"""Process-local one-time handoff over Day 27; no transport or durable ledger."""
from dataclasses import dataclass, replace
from threading import Lock
from uuid import uuid4
from day21_gate import Decision
from day24_recovery import Outcome, TASK
from day26_lifecycle import recover_with_lease
from day27_release import ReleaseQueue

POLICY = 'day28-delivery-boundary-v1'


@dataclass(frozen=True)
class Receipt:
    delivery_id: str
    recipient: str
    task: str


class DeliveryBoundary:
    """Trusted state/time only; all updates must pass through update().

    Returning an Outcome is the simulated handoff. The lock covers validation,
    consumption and that return decision, not downstream use of returned text.
    Restart loses pending entries and consumption history. Private fields are
    implementation state, not an interface for untrusted callers.
    """
    def __init__(self, state):
        self._lock = Lock()
        self._queue = ReleaseQueue(state)
        self._pending = {}
        self._consumed = set()

    def update(self, state):
        with self._lock:
            self._queue.update(state)

    def accept(self, ticket, candidate, *, original, now):
        """Return a text-free receipt, or None when Day 27 rejects admission."""
        with self._lock:
            result = self._queue.enqueue(ticket, candidate, original=original, now=now)
            if not result.released:
                return None
            receipt = Receipt(uuid4().hex, ticket.state.snapshot.principal, TASK)
            # Retain the original audit outcome, not candidate bytes.
            self._pending[receipt.delivery_id] = (receipt, ticket, now, result)
            return receipt

    def prepare(self):
        with self._lock:
            return self._queue.prepare()

    def deliver(self, delivery_id, *, recipient, task, now):
        with self._lock:
            def deny(reason):
                return Outcome(False, None, reason, False, None, (), None, (), POLICY)

            if type(delivery_id) is not str:
                return deny('invalid_delivery_id')
            if delivery_id in self._consumed:
                return deny('consumed_delivery_id')
            entry = self._pending.get(delivery_id)
            if entry is None:
                return deny('unknown_delivery_id')
            receipt, ticket, accepted_at, audit = entry
            if (type(recipient) is not str or type(task) is not str
                    or recipient != receipt.recipient or task != receipt.task):
                return deny('delivery_binding_mismatch')
            current = self._queue.prepare()
            if current.generation != ticket.generation or current.state != ticket.state:
                return deny('state_changed')
            # Delivery cannot predate queue acceptance. The caller must still
            # supply an independent, current clock on every attempt.
            if type(now) is not int or now < accepted_at:
                return deny('invalid_delivery_time')
            state = current.state
            result = recover_with_lease(
                '', original=Decision(False, None, ('blocked',)),
                before=ticket.state.snapshot,
                release_snapshot=replace(state.snapshot, now=now),
                lease=ticket.state.lease, release_lease=state.lease,
                authority=ticket.state.authority, release_authority=state.authority)
            if not result.released:
                return deny(result.reason)
            self._consumed.add(delivery_id)
            del self._pending[delivery_id]
            return replace(result, policy=POLICY, candidate_sha256=audit.candidate_sha256,
                           original_reasons=audit.original_reasons)
