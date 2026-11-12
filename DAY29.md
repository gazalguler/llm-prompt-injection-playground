# Day 29: persistent replay protection and crash recovery

2026-11-11 (America/Vancouver). Offline simulation using synthetic owner state.

Day 28 forgets consumed delivery IDs when the process stops. Day 29 adds a
SQLite replay ledger and `PersistentBoundary`, which reuses Day 28 admission and
last-moment authorization checks before claiming a stable operation ID. The
trusted application assigns that ID and must reuse it when retrying the same
operation, including after a restart. A new ID represents new work; this does
not deduplicate equivalent text or detect an application that invents retry IDs.

The ledger stores only the operation ID and a binding digest. The digest covers
the recipient, task, trusted records, source pins, revisions, lease and authority;
only the snapshot clock is excluded so fresh admission can use a later time.
Candidate text and rendered summaries are not stored. A consumed ID with another
binding is rejected rather than reassigned. Wrong recipient/task requests and
revoked authorization fail before any persistent claim.

Each claim opens the existing database, checks the schema, version and SQLite
integrity, then reads and inserts under `BEGIN IMMEDIATE`. The primary key and
transaction serialize separate workers. `synchronous=FULL` with a rollback
journal commits consumption before text can leave the wrapper. Missing, corrupt,
locked or incompatible storage returns no text or audit fields; opening a ledger
never silently creates a replacement. Initial provisioning is explicit and
refuses to overwrite an existing file.

Pending receipts are deliberately not durable. After a restart, the application
must re-admit using current trusted state and the same operation ID. A crash
before commit leaves no claim, so fresh admission may succeed. A crash after
commit leaves the ID consumed even if no caller received the outcome. This is a
**claim for simulated dispatch**, not proof of delivery. An uncertain commit
returns no text; a later retry may discover that consumption did commit. A storage
failure also consumes that attempt's in-memory receipt, requiring fresh admission.

Eleven new test methods cover reopening with a fresh clock, pending receipt loss,
two separate spawned workers racing for one ID, recipient/task mistakes, binding
replacement, revocation, missing/corrupt/incompatible storage, lock contention,
commit failures before and after persistence, abrupt process exits on both sides
of commit, explicit provisioning and malformed operation IDs. A successful
handoff runs with socket creation prohibited. The process-exit tests exercise
SQLite recovery, not physical power loss or storage hardware guarantees.

Validation: **210 unittest methods; 210 pytest tests and 555 subtests passed**.
Day 13 metrics, Days 16–19 and 21–24 historical checks, the Day 23 sealed review,
all five public package verifiers, the publication privacy scanner and
`git diff --check` passed. Historical evidence and frozen snapshots are unchanged.
The existing workflow discovers Day 29 without changes. No model was called.

```sh
.venv/bin/python -B -S -m unittest tests.test_day29_persistence -v
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
.venv/bin/python -B -S day21_publication_check.py
```

The database, operation IDs, state and clock belong to trusted application code.
Keep the same database across restarts: deletion, backup rollback or hostile
editing can defeat replay protection. State updates are ordered with dispatch
within each wrapper, but workers do not share live revocations; each must obtain
current authority independently. Claims are retained without pruning. There is
no network send, acknowledgement, distributed authorization service or exactly-once
external delivery guarantee. A committed claim can lose its simulated handoff.
