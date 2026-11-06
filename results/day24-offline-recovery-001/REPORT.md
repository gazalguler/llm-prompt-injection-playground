# Day 24: deterministic recovery, offline development evidence

The system discarded eight blocked Day 23 candidates and rendered eight accurate
incident summaries from independently supplied synthetic owner records. This is
application-level task completion, not a model defense result. **Original Qwen
resistance remains 0/4**, full success 2/4, partial compliance 2/4. The original
Day 22 gate still blocks 4/4 compromised attacks, falsely blocks 3/3 clean-correct
controls and achieves 0/8 safe released completion. Original labels are unchanged.

| Distinct measure | Result |
|---|---:|
| Recovery eligibility / blocked historical outputs | 8/8 |
| Accurate system-rendered completion / historical tasks | 8/8 |
| Historical final abstention | 0/8 |
| Historical false release / unsupported rendered claims | 0/8; 0/8 |
| New synthetic complete expected outcomes | 34/34 |
| Synthetic accurate final completion | 9/34 |
| Synthetic final abstention | 25/34 |
| Synthetic false abstention / eligible | 0/9 |
| Synthetic false release / ineligible | 0/25 |
| Synthetic unsupported summaries / released | 0/9 |

## Method and evidence

`evidence.json` holds each original candidate, original semantic review, original
gate disposition, simulated owner context, recovery outcome and expected summary.
It also includes all 34 new fixtures, their before/release snapshots, expectations
and actual outcomes. `summary.json` keeps model behavior, original blocking,
recovery and synthetic results separate with explicit denominators. The frozen
snapshot includes exact source modules, tests, fixtures, replay, original caller
plan and the unchanged sanitized Day 23 package. The verifier checks source
anchors before executing the frozen offline replay, reproduces original Day 23
gates/judgments with its published verifier, checks owner facts against the
original plan and independently derives publication metrics.

Recovery supports one allowlisted duration/restoration task, bounded integer
minutes and three finite components under an explicit restart-restored-service
relation. Every supplied record must match identity, schema, revision, digest,
provenance, authentication flag and freshness policy. Sources must agree;
duplicate/ambiguous sources abstain. Missing facts, unsupported tasks, stale or
future facts, revoked authorization and mid-request revision changes abstain.
Candidate words cannot select facts, templates or task routing. Every recovery is
labeled `System-rendered incident summary:`. The rejected multilingual control's
invented database-failure cause is absent from its new 92-minute/database-restart
summary; its original contamination and failed-task labels remain unchanged.

**Authenticated real-world source integration is outside this experiment.**
Source IDs, verified flags, authorization and time values are synthetic adapter
fixtures. Their incident values/revisions come from the original trusted caller
plan, never extraction from model or tool text. They do not authenticate themselves
and do not constitute real current telemetry. An application must authenticate
sources and users independently, supply the complete current record set, correctly
map the whole requested task and hold a transaction/lease through delivery. No
such adapter, credentials, signature verification or real delivery transaction
was implemented or evaluated. A poisoned trusted record with matching pins can
produce a false summary; a retained regression test demonstrates this limit.

## Reproduce without repository, model or credentials

Copy this entire directory, then run with Python 3.13 (standard library only):

```sh
python -B -S verify.py --public-only
```

From a repository checkout, omit `--public-only` to additionally compare current
source bytes and invoke the original Day 23 verifier's available sealed private
linkage checks. A standalone copy does not contain private raw archives. CLI
replay/verifiers forbid sockets; no inference, model preflight, retries, cloud
fallback or downloads are performed. Bytecode writes are disabled in subprocesses.
`SHA256SUMS.json` covers every file except itself; the verifier enforces exact
inventory and embeds frozen-source anchors, so recomputing a manifest alone cannot
conceal source, fixture or result edits.

## Limits

These are development replays informed by Day 23 failures plus authored fixtures,
not blinded or independently held-out evaluation. Original reviews and new fixture
expectations share study authorship. Exact expected strings test this finite
renderer, not general semantic entailment or jailbreak robustness. Source truth,
authenticity, availability, completeness and upstream routing remain assumptions.
Deterministic rendering does not prove model resistance or source authenticity.
Checksums and embedded anchors are not signatures or independent attestations;
replacing the verifier and its anchors is outside the integrity claim. Public raw
hash references alone cannot establish private raw-byte linkage or audit historical
egress/server metadata. Small synthetic counts do not estimate production rates.

No historical source, plan, judgment, response, public package or sealed archive
was rewritten. Publication adds no model calls and does not authorize future
inference. See the repository's `DAY24_PUBLICATION.md` for validation results and
an exact review/staging list. No staging, commit or push is part of preparation.
