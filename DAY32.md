# Day 32 — End-to-End Delivery Reliability & Failure Injection

November 17, 2026 (America/Vancouver)

Day 30 persists a send intent and revalidates current authorization before
issuing a leased claim. Day 31 commits the operation receipt and simulated
effect in one receiver transaction. Day 32 runs those components together
against two SQLite databases in a synchronous, offline simulation.

Each attempt uses an explicit integer clock and the outbox's existing five-second
lease and three-attempt budget. The outbox rechecks the stored authorization
context and rendered text against current trusted state. The simulation keeps
the claim in memory and checks the entire batch of transport frames before
calling the receiver. Every frame must carry the same recipient, task,
operation ID, lease token, and exact rendered text. The receiver uses the
operation ID as its idempotency key and checks the recipient, task, and payload
binding independently. The sender records acknowledgement only after the
receiver returns a committed applied or duplicate result and the outbox still
accepts the claim token.

## What the fault tests observed

| Injection | Observed result |
| --- | --- |
| Lost acknowledgement after receiver commit | The sender remained leased. A retry before lease expiry could not claim the row. After expiry, a fresh worker or Python process received a duplicate result and completed the sender row. One receipt and one effect persisted. |
| Temporary transport outage and duplicate frames | The outage left the receiver empty. The next attempt delivered two copies in sequence. The receiver applied the first and deduplicated the second. |
| Concurrent retries at lease expiry | Two workers with separate outbox and receiver instances raced against the same databases. One claimed and acknowledged the duplicate; the other could not claim it. |
| Wrong route or key, altered frame, revoked authority | An unknown key, wrong recipient or task, and a retry after revocation failed at the claim. Changes to any of the five frame fields stopped the batch before any receiver write. A receiver configured for a different recipient also rejected the attempt. |
| Locked sender database | Claim failed before receiver processing and left the sender pending. A later attempt completed after the lock was released. |
| Receiver effect insert failure and sender acknowledgement write failure | An abort trigger rolled back both receiver rows. After repair, the receiver committed one effect, but an acknowledgement trigger left the sender leased. The third attempt deduplicated and marked the sender done. |
| Persistent transport outage | Three failed attempts consumed the retry budget. The next attempt obtained no claim, and no effect had occurred. |

## Verification

Python 3.13.18 collected **243 distinct test methods** in the configured
project suite. Unittest and pytest each reported **238 passed and five skipped**.
Pytest also reported 580 passing subtests. The ten new Day 32 methods passed
under both runners. The method count includes each method once.

Day 13 metrics, Days 16–19 and 21–24 historical replay checks, all five public
package verifiers, and the publication privacy scan passed. The five skipped
methods require the private Day 23 raw archive. The standalone sealed review
also could not open its private manifest. Public verification succeeded
within the available evidence, while linkage to private original bytes
remained unavailable. No historical evidence was modified. No model, paid API,
or external delivery calls were made.

```sh
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
.venv/bin/python -B -S day21_publication_check.py
```

## Limits

The at-most-one effect property applies to a retained receiver database and a
stable operation key. Receipt and effect commit together there, while sender
acknowledgement is a separate transaction. An effect can exist while the sender
remains leased, and retry exhaustion, revocation, expiry, or storage failure can
prevent eventual delivery. These outcomes rule out an end-to-end exactly-once
guarantee. An effect outside the receiver transaction requires its own atomic
idempotency mechanism.

The simulator compares frames to a claim held within a trusted call. It assumes
trusted caller state, time, code, and private storage. It has no remote identity
protocol or independent receiver-side authorization check. Revocation is
checked on each claim, and cannot retract an already issued claim. Database
loss, restore, or tampering can defeat deduplication. The tests exercise local
SQLite transactions and fresh processes, without measuring network behavior
or durability under power loss. Receipt and effect rows are retained indefinitely.
