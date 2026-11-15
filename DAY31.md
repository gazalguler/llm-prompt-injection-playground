# Day 31: receiver-side idempotency and duplicate delivery protection

2026-11-14 (America/Vancouver). Offline development with synthetic owner state.

Day 30 retries an outbox claim when its lease expires. A receiver may already
have applied the first attempt even though the sender received no acknowledgement.
`day31_receiver.py` adds a SQLite receiver and a `dispatch` function that uses the
existing `Outbox.claim` and `Outbox.ack` methods. Day 28–30 implementations and
historical experiment files are unchanged.

The trusted application reuses the outbox operation ID as the receiver's global
idempotency key. `Receiver.receive` binds it to the exact recipient, task and
rendered text. A matching retry returns `duplicate`; a different binding returns
no acknowledgement and leaves the original rows intact. Lease tokens are excluded
from this binding because Day 30 creates a new token on each retry. A new operation
ID represents new work, even when its text matches an earlier operation.

The receiver opens explicitly provisioned storage without creating a replacement.
Each request uses its own SQLite connection, checks the schema, version, database
integrity and foreign keys, then reads or inserts under `BEGIN IMMEDIATE`.
The receipt and simulated effect are inserted in the same transaction. The effect
is a row in the `effects` table containing the rendered payload; no external
service is called. Primary keys and SQLite's write transaction serialize competing
processes. Transactions use a rollback journal and `synchronous=FULL`.

The receiver returns success only after commit. A storage error, binding mismatch
or uncertain commit returns `None`. `dispatch` acknowledges the outbox only after
`applied` or `duplicate`. A crash after receiver commit and before sender
acknowledgement leaves one effect; a later claim with the same key observes the
receipt and can acknowledge without another effect. Sender acknowledgement still
uses Day 30's token and lease checks. The two databases do not share a transaction.

Ten new test methods cover:

- repeated deliveries and receiver reopening, with socket creation prohibited;
- a lost acknowledgement followed by an expired-lease retry through the existing
  outbox, stale-token rejection and the final done state;
- changed payload, recipient and task, a new lease token, and distinct keys;
- two spawned processes requesting the same key, with one `applied` result and one
  `duplicate` result and exactly one stored effect;
- an insertion trigger that aborts the effect write, proving the receipt rolls
  back too and the outbox is not acknowledged until a later successful retry;
- missing, corrupt, incompatible and locked receiver storage;
- injected errors before and after commit, followed by retry reconciliation;
- abrupt subprocess exits before and after receiver commit, using actual outbox
  claims and SQLite recovery;
- provisioning collisions and malformed inputs.

These are authored regression tests of an application state machine. They do not
measure model resistance or establish performance under production traffic.

Validation with Python 3.13: unittest discovered **233 unique test methods: 228
passed and five skipped**. Pytest ran the same methods: **228 passed, five skipped,
570 subtests passed**. Runner totals are not added together, and subtests are not
counted as additional unique methods. The five existing Day 23 review tests require
a private raw archive absent from this fresh checkout. Its sealed raw-byte review
could not be rerun. Public Day 23 evidence verification passed, but does not replace
that private check.

Day 13 metrics, Days 16–19 and 21–24 historical replay checks, all five publication
package verifiers, the publication privacy scanner and `git diff --check` passed.
The publication verifiers also state where private original-byte linkage is
unavailable. Historical experiment data and frozen publication snapshots were
preserved. No model, Ollama, paid API or external delivery calls were made.

Reproduce the suites and privacy scan:

```sh
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
.venv/bin/python -B -S day21_publication_check.py
```

The existing GitHub Actions workflow runs the historical checks, five verifiers
and both test runners. Publication status must be checked against the pushed
commit's Actions run; local validation alone does not establish completion.

The guarantee is SQLite-transactional idempotency for these local effect rows.
It is not exactly-once network delivery. A remote payment, email or other effect
outside this SQLite transaction would need its own atomic idempotency mechanism.
Delivery can still fail or stop because of authorization expiry, retry limits,
revocation, storage failure or unavailable workers. Old claims cannot retract
already released text. `dispatch` obtains current authority through Day 30;
`receive` itself does not authenticate callers, validate current authorization or
verify a claim signature. Caller identity, receiver configuration, operation IDs,
clock and storage are trusted application inputs.

Receipts and effects are retained without pruning. Deleting, restoring an older
backup of, or maliciously editing the receiver database can allow repeated
effects. It stores rendered text and must remain private local application data.
The tests use temporary databases and publish none. Process exits exercise SQLite
recovery, not physical power loss, hardware failure or distributed consensus.
