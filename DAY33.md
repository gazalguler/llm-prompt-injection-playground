# Day 33 — Fault Injection & Recovery Invariants

November 18, 2026 (America/Vancouver)

The Day 32 delivery path uses separate SQLite databases for the sender and
receiver. To see what survives when a worker disappears, the tests run the
existing code in a child Python process and exit it immediately before or after
each selected commit. The pre-commit stops come after the SQL writes, leaving
SQLite to recover the open transaction when the parent reopens the database.
The post-commit stops happen before the caller receives the transaction result.
No production hooks are needed.

| Transaction | Stop before commit | Stop after commit |
| --- | --- | --- |
| Queue intent | No sender row survives. | The original pending row survives. Enqueuing the same intent again keeps that row. |
| Claim | The row stays pending with zero attempts. | The lease and its attempt count survive. The receiver remains empty. |
| Receiver receipt and effect | Neither receiver row survives. | Both rows survive while the sender remains leased. |
| Sender acknowledgement | The effect survives and the sender stays leased. | The effect and completed sender status survive. A later claim is rejected. |

Each recoverable case finishes with one receipt and one effect for the original
operation key and payload. A live lease blocks early retry. At expiry, a retry
applies the effect if the receiver transaction rolled back or gets a duplicate
result if it committed. In a separate lost-acknowledgement schedule, two workers
race to reclaim the lease. Only the winner can finish delivery. While that lease
is active, the old token and an incorrect token both fail to acknowledge it.

Changing the operation ID in a retry frame prevents both receiver processing and
sender acknowledgement. Revoking the authority then blocks the next claim.
Neither step changes the receipt and effect already on disk. Three simulated
transport failures exhaust the retry budget, so restoring the transport alone
leaves the operation undelivered.

## Verification

Unittest and pytest collected the same **248 unique test methods**. Each reported
**243 passed, five skipped and zero failed**. Pytest recorded **588 passing
subtests**, including the eight transaction stops. Day 13 metrics, historical
replays for Days 16–19 and 21–24, all five public package verifiers, and the
publication privacy scan passed. The five skips and the standalone Day 23 sealed
review require the unavailable private archive. Historical evidence remained
intact. The checks used no live models or paid APIs.

## Limits

The matrix covers selected process exits around SQLite commits with a trusted
clock, caller and local storage. It does not test power loss, arbitrary crash
timing or a remote network. The at-most-one effect property depends on retaining
the receiver database and operation key. The sender can remain leased after the
effect commits because acknowledgement is a separate transaction. Recovery
requires a usable retry, valid authority and available storage and transport.
Permanent outages can prevent progress, and this setup provides no end-to-end
exactly-once delivery guarantee.
