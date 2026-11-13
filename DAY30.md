# Day 30: transactional outbox and crash recovery

2026-11-12 (America/Vancouver). Synthetic offline simulation.

Day 29 commits consumption before returning text, so a crash can lose a handoff.
Day 30 adds a separate `Outbox` adapter using the existing Day 28 admission and
delivery checks. The Day 29 ledger and historical evidence remain unchanged.
The trusted application supplies a stable operation ID, current state and time.

Enqueue validates the prepared ticket and stores the intended rendered text,
complete authorization context and pending status in one SQLite transaction.
Candidate text is discarded. An identical enqueue is idempotent, including after
acknowledgement; another context cannot replace the same ID. Only the snapshot
clock is excluded from context comparison, allowing fresh clocks after restart.
The database now contains trusted records and rendered text: it is private local
application storage, not a public evidence package.

Claim revalidates current authorization, freshness, recipient and task before
checking the stored context and text. `BEGIN IMMEDIATE` serializes claims across
processes. A committed claim records a random fencing token, lease deadline and
attempt count before returning a simulated handoff. Another worker can reclaim
an expired lease with a new token. Acknowledgement marks the row done only when
the token still owns an unexpired lease. Old tokens cannot acknowledge later
attempts. The default is three attempts and a five-second lease; trusted callers
must use consistent retry settings. Exhausted rows stay stored for inspection.

Missing, corrupt, locked or incompatible storage fails closed. Opening does not
create storage; provisioning refuses to overwrite a file. Transactions use a
FULL synchronous rollback journal. Uncertain commits return no handoff; a later
attempt observes either the rollback or the committed lease. Enqueue uncertainty
can be resolved by retrying the same operation ID. Time cannot precede admission
or the last committed claim, but the caller remains responsible for a trustworthy
clock. Tests use explicit integer times, not sleeps.

Thirteen new regression methods cover durable restart, duplicate enqueue,
context replacement, lease expiry, acknowledgement loss, stale tokens, bounded
retries, clock rollback, current authorization and recipient checks, two spawned
processes claiming one lease, storage failures, uncertain commits and abrupt
process exits before/after enqueue commit and after claim. A simulated receiver
shows two effects without deduplication and one keyed effect for the same ID.
A handoff and acknowledgement also run with socket creation prohibited.

Validation: **223 distinct unittest methods passed; the same 223 tests passed
under pytest, with 571 subtests passed**. Neither runner reported failures or
skips. Day 13 metrics, Days 16–19 and 21–24 historical replays, the Day 23 sealed
review, all five public package verifiers, the publication privacy scan and
`git diff --check` passed. The existing push/PR workflow discovers the new tests
without modification. Historical evidence and frozen snapshots are unchanged.

```sh
.venv/bin/python -B -S -m unittest tests.test_day30_outbox -v
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
.venv/bin/python -B -S day21_publication_check.py
```

This is a recovery state machine, not a network transport. A crash after a
receiver applies an effect but before acknowledgement can cause a duplicate on
retry. Receiver-side deduplication of the stable operation ID is required to
avoid that duplicate; there is no exactly-once external delivery guarantee.
Retry limits, expiry and revocation can prevent eventual delivery. Claim expiry
cannot retract text already returned to an old worker. Each worker must obtain
fresh authority independently; updates serialize only within its local wrapper.
Database deletion, rollback or hostile editing defeats its guarantees. Rows are
retained without pruning. Process-exit tests do not establish power-loss or
hardware durability. No model, paid API or external delivery was called.
