# Day 27: authorization at queue insertion

2026-11-09 (America/Vancouver). Offline development using synthetic owner state.

Day 26 requires its caller to keep the final authorization check and delivery
serialized. Day 27 supplies a small adapter with a narrower, executable boundary:
checking and appending the rendered outcome to an in-memory queue under one lock.
`ReleaseQueue.update()` uses the same lock and advances a process-local generation
on every update. A prepared ticket binds that queue, generation and state. An
intervening update aborts the transaction, even if the original values are restored.
A new ticket must pass the existing Day 24–26 checks against current trusted time.

The ten new test methods exercise successful queue insertion and audit retention,
revocation between preparation and use, a revised record with a matching new grant,
change-and-restore, source swaps and mixed sources, clock rollback and expiry,
malformed state, tickets from another queue, discarded-candidate requirements and
candidate instructions. They also show the limits: revocation after insertion does
not retract a queued item; restarting with old trusted state permits replay; a
valid ticket can be used repeatedly. These are deterministic interleavings, not a
concurrent stress test or a held-out model evaluation. A successful path runs with
socket creation prohibited.

Only trusted application code may supply state and time, and every state change
must go through the adapter. Private-field mutation bypasses the boundary. The
lock protects this queue in one process; it provides no durable epoch ledger,
authentication, signatures, external delivery transaction or cross-process lock.
A later consumer would need its own authorization boundary. Trusted poisoning and
complete-state rollback remain possible. No model server or paid API was called;
historical evidence and sealed publication packages are unchanged.

Local validation: **187 unittest methods passed; 187 pytest tests and 526
subtests passed** (Day 26 baseline: 177 methods). Day 13 metrics, Days 16–19/21–24
historical checks, the sealed Day 23 review and all five published package
verifiers passed. The publication scanner includes the three new Day 27 files;
its secret, local-path and email patterns found no matches across 118 candidate
files. `git diff --check` passed. Existing CI discovers the new tests without a
workflow change. No new publication archive was needed.

Reproduce:

```sh
.venv/bin/python -B -S -m unittest tests.test_day27_release -v
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
.venv/bin/python -B -S day21_publication_check.py
```
