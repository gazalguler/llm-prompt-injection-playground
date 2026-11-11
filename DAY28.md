# Day 28: delivery boundary and replay protection

2026-11-10 (America/Vancouver). Offline development with synthetic owner state.

Day 27 checks authorization when inserting an item into a local queue. Day 28
adds `DeliveryBoundary`, which uses that adapter for admission and checks again
when a consumer requests the text. Admission returns a frozen receipt containing
an opaque delivery ID, recipient and task; it does not return the queued summary.
The recipient is the approved snapshot principal, not an independently chosen
address. This experiment supports the existing incident-summary task only.

The server-side pending entry binds the ID to the Day 27 ticket, acceptance time
and audit outcome. That ticket binds the queue instance, state generation and
exact owner snapshot, including source, record, revision, digest and provenance.
Every state update uses the same outer lock as admission and delivery. A changed
generation rejects old entries even if the original state is later restored.
Delivery reuses the Day 24–26 snapshot, source-policy and lease checks with the
current trusted time. It also rejects time before acceptance. Successful delivery
consumes the ID and removes its pending entry under the lock before returning the
rendered outcome. Repeated or concurrent calls with that ID cannot return text
again. Separate admissions intentionally receive separate IDs for the same work.

Wrong recipient/task bindings, altered or foreign IDs, withdrawn authorization,
expired leases, stale facts and replaced state return no text, hashes, provenance
or original reasons. Failed delivery attempts do not consume the ID: a binding
mistake can be corrected, but a state-generation change permanently invalidates
that pending entry. Successful handoffs preserve the original audit fields. The
adapter retains hashes rather than candidate bytes; it never interprets candidate
instructions. Day 27 retains its internal queue history in memory.

Twelve new test methods cover admission versus handoff, retained audit fields,
duplicate IDs, distinct admissions, twelve simultaneous consumers, revocation,
withdrawal, missing grants, expiry and freshness boundaries, time rollback,
record/source replacement with matching new grants, change-and-restore, wrong
recipients/tasks, altered and foreign IDs, immutable receipts, inherited admission
checks and rejection privacy. A controlled two-thread interleaving holds the
validation step while an update waits; the successful handoff precedes that
update. Another test shows that a later update cannot retract already returned
text. A successful handoff also runs with socket creation prohibited. These are
authored development regressions, not a held-out attack or model evaluation.

Local validation: **199 unittest methods passed; 199 pytest tests and 547 subtests
passed** (Day 27 baseline: 187 methods and 526 subtests). Day 13 metrics, Days
16–19/21–24 historical checks, the Day 23 sealed review and all five publication
package verifiers passed. The publication scanner checked 121 explicit candidate
files without secret, local-path or email pattern findings. `git diff --check`
passed. Existing CI discovers the tests without a workflow change. No new replay
archive was needed; historical experiments and frozen package snapshots are
unchanged.

Reproduce:

```sh
.venv/bin/python -B -S -m unittest tests.test_day28_delivery -v
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
.venv/bin/python -B -S day21_publication_check.py
```

Returning the outcome is the simulated delivery boundary. There is no network
send, acknowledgement, crash recovery or transaction with an external consumer.
The lock orders trusted state updates and handoffs within one process; it cannot
control later use of returned text. A restart loses pending entries and the
consumed-ID ledger, and the same work can be admitted again. Consumption history
and queue history are unbounded in this small experiment. There is no durable
idempotency guarantee, cross-process exclusion, production authentication or
signature verification. Recipient identity, state and current time must come
from trusted application code; arbitrary private-field mutation or a false clock
bypasses that assumption. Complete trusted-state rollback and poisoned owner facts
remain outside the guarantee. No Ollama, OpenAI or other inference was called.
