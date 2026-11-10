"""Offline in-memory check-and-enqueue adapter; no external delivery or storage.

Only trusted application code may construct state or supply time. All state
updates must use update(); mutating private fields bypasses this boundary.
"""
from dataclasses import dataclass, replace
from threading import Lock
from day24_recovery import Snapshot, recover_rejected
from day26_lifecycle import Authority, Lease, recover_with_lease

POLICY = 'day27-check-and-enqueue-v1'


@dataclass(frozen=True)
class State:
    snapshot: Snapshot
    lease: Lease
    authority: Authority


@dataclass(frozen=True)
class Ticket:
    owner: object
    generation: int
    state: State


class ReleaseQueue:
    """Serialize trusted updates with final validation and local queue insertion.

    A generation change aborts even when values later return to their old state.
    This is process-local and reusable, not durable or single-use authorization.
    The queue records authorization at enqueue time, not at later delivery time.
    """
    def __init__(self, state):
        self._lock = Lock()
        self._owner = object()
        self._generation = 0
        self._state = state
        self._outbox = []

    def update(self, state):
        with self._lock:
            self._generation += 1
            self._state = state

    def prepare(self):
        with self._lock:
            return Ticket(self._owner, self._generation, self._state)

    def queued(self):
        with self._lock:
            return tuple(self._outbox)

    def enqueue(self, ticket, candidate, *, original, now):
        with self._lock:
            reason = None
            if type(ticket) is not Ticket or ticket.owner is not self._owner:
                reason = 'foreign_or_invalid_ticket'
            elif ticket.generation != self._generation or ticket.state != self._state:
                reason = 'state_changed'
            elif type(self._state) is not State or type(self._state.snapshot) is not Snapshot:
                reason = 'invalid_state'
            if reason:
                result = recover_rejected(candidate, original=original, before=None,
                                          release_snapshot=None)
                return replace(result, reason=reason, policy=POLICY)
            state = self._state
            result = recover_with_lease(
                candidate, original=original, before=ticket.state.snapshot,
                release_snapshot=replace(state.snapshot, now=now),
                lease=ticket.state.lease, release_lease=state.lease,
                authority=ticket.state.authority, release_authority=state.authority)
            result = replace(result, policy=POLICY)
            if result.released:
                self._outbox.append(result)
            return result
