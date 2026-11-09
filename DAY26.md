# Day 26: authorization lease lifecycle

2026-11-08 (America/Vancouver). Offline development; no new inference or live
identity integration. Historical evidence and sealed packages are unchanged.

Day 25 checks whether owner policy permits the exact principal, task, incident,
source, revision, digest and provenance. It does not distinguish an old grant
from a current grant when their content is identical. Day 26 adds an explicit
lease ID, authorization epoch and half-open validity interval
`not_before <= now < expires_at`. An independently supplied owner authority state
provides the current epoch and revoked lease IDs. A lease with a different epoch,
a revoked ID or an inactive interval cannot release text.

`day26_lifecycle.py` checks both trusted snapshots and both lifecycle states.
The lease and authority state must remain identical between checks, even for an
unrelated revocation. Renewal is a new transaction. The unchanged Day 25 policy
checks and Day 24 deterministic renderer still apply; candidate instructions
cannot renew a lease or supply incident facts. Failed checks return no text or
release provenance. Successful outcomes retain the existing audit fields and
identify the Day 26 policy.

Ten new test methods use synthetic incident records, trusted time and owner
state. They cover active release and audit retention, validity boundaries,
replayed leases against older/newer authority epochs, revocation at either
check, renewal, mid-check changes, malformed types, mixed sources, inherited
snapshot/policy checks and the complete-state replay limitation. Mixed-source
cases require a grant for each source and agreement between independently pinned
records: an ungranted agreeing source and a granted conflicting source both
abstain. An allowed transaction is also exercised with sockets prohibited.

Local results: **177 unittest methods passed; 177 pytest tests and 510 subtests
passed**. This adds ten methods to the locally verified Day 25 baseline of 167.
Day 13 metrics, Days 16–19/21–24 offline checks, the Day 23 sealed review, all five
published package verifiers and the publication scanner passed. Git whitespace
and publication-file scans passed. Existing CI discovers the new tests without a
workflow change. These same-author development regressions are not a held-out
benchmark or evidence of improved model resistance.

Reproduce without a model server:

```sh
.venv/bin/python -B -S -m unittest tests.test_day26_lifecycle -v
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
.venv/bin/python -B -S day21_publication_check.py
```

The caller must obtain time, authority and lease state independently of model or
retrieved text. It must persist monotonic epochs, advance the epoch on revocation
or policy changes, issue a fresh ID on renewal, and serialize the final check and
delivery. This module does not implement that storage, authentication, signatures,
one-time consumption or a live revocation service. Replaying *all* trusted state
still succeeds; a regression makes that limit explicit. Repeated valid calls also
succeed, so this is not single-use replay protection. Trusted poisoning and hidden
upstream conflicts retain the earlier limitations. A next step is an offline
adapter test with durable epoch storage and restart/rollback scenarios before
considering any real identity integration.
