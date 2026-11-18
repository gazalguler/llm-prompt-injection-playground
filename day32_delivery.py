"""Synchronous offline delivery over the Day 30 outbox and Day 31 receiver."""
from dataclasses import dataclass
from enum import Enum


class Fault(Enum):
    NONE = 'none'
    TRANSPORT_UNAVAILABLE = 'transport_unavailable'
    DUPLICATE_MESSAGE = 'duplicate_message'
    LOST_ACK = 'lost_ack'


@dataclass(frozen=True)
class Message:
    operation_id: str
    token: str
    recipient: str
    task: str
    payload: str

    def matches(self, expected):
        return all(
            type(value) is str and value == original
            for value, original in (
                (self.operation_id, expected.operation_id),
                (self.token, expected.token),
                (self.recipient, expected.recipient),
                (self.task, expected.task),
                (self.payload, expected.payload),
            )
        )


@dataclass(frozen=True)
class OfflineTransport:
    fault: Fault = Fault.NONE

    def frames(self, message):
        if self.fault is Fault.TRANSPORT_UNAVAILABLE:
            return ()
        if self.fault is Fault.DUPLICATE_MESSAGE:
            return (message, message)
        return (message,)


@dataclass(frozen=True)
class Attempt:
    status: str
    receiver_results: tuple[str, ...] = ()


def deliver(outbox, receiver, operation_id, *, recipient, task, now,
            transport=OfflineTransport()):
    """Run one attempt with a trusted clock and current state in the outbox.

    The authorized claim stays in this call. No transport frame can establish
    authority or supply a receiver response. Each retry must claim again.
    """
    if type(transport.fault) is not Fault:
        return Attempt('invalid_transport')
    claim = outbox.claim(operation_id, recipient=recipient, task=task, now=now)
    if claim is None:
        return Attempt('claim_unavailable')

    expected = Message(claim.operation_id, claim.token, recipient, task, claim.outcome.text)
    frames = transport.frames(expected)
    if type(frames) is not tuple:
        return Attempt('invalid_message')
    if not frames:
        return Attempt('transport_unavailable')
    if any(type(frame) is not Message or not frame.matches(expected) for frame in frames):
        return Attempt('invalid_message')

    results = []
    for frame in frames:
        result = receiver.receive(claim, recipient=frame.recipient, task=frame.task)
        if result not in ('applied', 'duplicate'):
            return Attempt('receiver_unconfirmed', tuple(results))
        results.append(result)
    if transport.fault is Fault.LOST_ACK:
        return Attempt('ack_lost', tuple(results))
    if not outbox.ack(claim, now=now):
        return Attempt('ack_unconfirmed', tuple(results))
    return Attempt('done', tuple(results))
