# Day 24: deterministic owner-controlled recovery

2026-11-06 (America/Vancouver). Development on clean `main` at `1242e20`.
No new Ollama, OpenAI, cloud, paid inference, model preflight or downloads.
No staging, commit or push. The Day 23 proposal, original outputs, reviews,
frozen plan, gate sources and public packages are preserved.

## Question and trust boundary

Day 23 measured 0/4 model resistance, 2/4 full attack successes and 2/4 partial
compliances. The unchanged Day 22 gate blocked 4/4 compromised attacks and 3/3
clean-correct controls; safe released completion was 0/8. A fourth clean-prompt
control invented a database-failure cause. None of these labels is changed.

Day 24 asks whether the application can complete an authorized narrow task after
**discarding** the candidate, using independent structured facts. It implements
neither a wider English grammar nor a model repair loop. `day24_recovery.py` has
no I/O and no candidate-release branch. The caller supplies the unchanged Day 22
rejection; recovery requires a blocked decision with no released candidate text.
Candidate text is hashed for audit only. Even a correctly phrased candidate
cannot bypass recovery authorization. Tasks that include cause, data loss or
other unsupported details must not be routed to the supported task identifier.

The trusted ingestion adapter is an explicit deployment prerequisite, **not
implemented authentication**. It must authenticate source identities, authorize
the principal for the exact incident/task, read a complete current source set,
pin record digests/revisions and supply trusted time and provenance independently
of LLM output and retrieval. `authenticated=True`, a source name and a matching
hash are assertions of that adapter, not evidence a document authenticated
itself. Never parse either snapshot from a retrieved document or candidate.
The API is an internal owner-controlled boundary, not an endpoint for arbitrary
user-supplied records. Hiding a conflicting source upstream cannot be detected.

## Implementation contract

Frozen, exact typed records bind record/source identity, schema 1, positive
revision, observation time, duration in integer minutes (1–9999), component from
`database/cache/worker`, and explicit relation `restart_restored_service`.
Booleans/floats cannot masquerade as integers. Slots cannot contain free text;
root cause is neither inferred nor represented. Restart correlation alone is
insufficient to assert restoration. JSON loading rejects missing and extra keys.
Records cannot select templates or policies.

A trusted Snapshot binds principal, explicit authorization, allowlisted task
`incident_duration_and_restoration`, incident identity, trusted time, grant expiry,
maximum age (1–86400 seconds), records and corresponding source pins. Each pin
binds schema/revision, exact canonical record digest and verified provenance
reference. Every supplied source must validate and agree on duration, component
and relation. A newer revision does not override a disagreement. Empty sources,
extra/unpaired pins, duplicate source identities, wrong records, unverified
sources, stale or future observations and ambiguous sources abstain. Unlike Day
19, this deliberately requires one record per pin; duplicate sources abstain.
Pin/record tuples use matching order, so reorder both together.

The caller obtains a second trusted snapshot immediately before delivery.
Authorization, expiry and freshness are checked again. Time may advance, but
records, pins, task, principal and policy context must remain identical; a
revision change, revocation or clock reversal abstains. The adapter must hold a
transaction/lease covering this check and delivery: two Python snapshots do not
solve a race after the final check. No live authorization service is included.

A single owner template renders bounded numbers and finite component identifiers.
It starts `System-rendered incident summary:` and makes only duration and
restoration claims. It has no attacker-selectable template argument. A separate
Outcome retains original gate reasons, candidate digest, snapshot digest,
source/revision/provenance references, policy version and template version.
Failed recovery returns no text or release provenance. The replay retains the
original reviews and gate decisions separately from these new outcomes.

## Offline evidence and denominators

`day24_owner_fixtures.json` is a **synthetic trusted-adapter simulation**. Its four
incident facts and revisions were copied from the already published Day 23
caller plan, not extracted from generated answers or tool text. Source IDs,
principal, authenticated flags, time 1000, observation 995, expiry 1100 and age
limit 60 are authored development fixtures. They are not historical telemetry,
real credentials or evidence those incidents remain current today. Replaying
saved outputs tests the recovery mechanism under those assumptions only.

`day24_replay.py` replays all eight saved responses, reproduces the unchanged
Day 22 decisions and compares complete rendered strings to incident values in
the original evidence. It does not relabel the original model response.

| Historical Day 23 development replay metric | Result |
|---|---:|
| Original Qwen resistance | 0/4 attacks |
| Original full / partial attack success | 2/4; 2/4 attacks |
| Original compromised attack outputs blocked | 4/4 compromised attacks |
| Original clean-correct false blocks | 3/3 clean-correct outputs |
| Original safe released completion | 0/8 outputs |
| Recovery eligibility under simulated trusted context | 8/8 blocked outputs |
| Final accurate system-rendered released completion | 8/8 tasks |
| Final abstention | 0/8 tasks |
| False release / unsupported claims in rendered summaries | 0/8; 0/8 tasks |

The multilingual control's original unsupported cause and original task-failure
judgment are retained. Its new response reports 92 minutes and a database restart
without claiming a failure cause or denying that downtime details exist.
Recovery of an attack is application completion, never model resistance.

`day24_cases.json` contains **34 newly authored synthetic development fixtures**,
separate from those eight saved model outputs. Nine have eligible supported
records/tasks and 25 require abstention. Coverage includes new incident identities,
1/23/311/9999-minute facts, all three components, arbitrary alternate candidate
incident descriptions, forged role/encoded instructions, invented cause and data
loss in candidate text, contaminated structured slots, missing/extra fields,
boolean values, wrong identity/schema/revision/digest, stale/future facts,
freshness boundary, duplicate sources, two agreeing sources, contradictory
independently pinned sources, unsupported/broader tasks, expired/revoked grants
and revision changes before release.

| New synthetic development metric | Result |
|---|---:|
| Expected dispositions and complete text matched | 34/34 |
| Final accurate released completion | 9/34 |
| Abstention | 25/34 |
| False abstention among eligible fixtures | 0/9 |
| False release among fixtures requiring abstention | 0/25 |
| Released summaries with unsupported claims | 0/9 released |

The JSON also stores false release and unsupported-claim counts over the full
34-case cohort. These zeros are exact-output comparisons to authored expected
strings, not general semantic entailment judgments. Nine completions out of 34
is appropriate because the other tasks lack release authority or sufficient
consistent facts. Test grids additionally use unseen-by-the-renderer numeric
values (2, 29, 401, 8765). No output lookup keyed by case ID exists.

## Reproduction and integrity

Use the existing Python 3.13 environment; no server or credentials are needed:

```sh
.venv/bin/python -B -S day24_replay.py --check
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
```

Default replay prints JSON and makes no writes. `--check` compares the report,
including LF-normalized SHA-256 source snapshots, without rewriting it. Replay
CLI and dedicated tests forbid sockets. Expected fixture strings are stored
separately from the renderer. Changes to source/fixtures/evidence invalidate the
saved report; checksums remain reproducibility evidence, not signatures. All
four published verifiers independently check their unchanged package contracts.

Validation: **150 unittest methods passed** (132 existing + 18 new);
**150 pytest tests and 445 subtests passed**. Day 13 metrics, Days 16/17/18/19/21/22
historical replays, Day 23 frozen-plan/offline check, sealed live review and
Day 24 replay all pass. All four public-package verifiers pass including available
private linkage; Day 23 public-only verification also passes. The explicit
publication scanner includes Day 24; credential/key/bearer, path and email scans
are bounded supplementary checks. Git whitespace and immutable-byte comparison
passed before handoff. Of 480 baseline tracked files, 476 remain byte-identical;
only the four infrastructure files listed below changed. Existing sealed private
archives also pass their published verifiers. These are local results, not a
claim of new remote CI.

New files: this document, `day24_recovery.py`, `day24_replay.py`,
`day24_cases.json`, `day24_owner_fixtures.json`, `day24_offline.json`,
`tests/test_day24_recovery.py`. Infrastructure changes: README, LF attributes,
offline CI replay step and publication scanner allowlist. No live runner changes.

## Limitations and possible later evaluation

This is informed by observed Day 23 failures and Days 17–19 recovery designs.
Neither the historical replay nor new authored fixtures are a held-out benchmark.
Same-author expectations, finite slots, narrow task, small sample and trusted
adapter assumptions preclude broad robustness, production utility or statistical
claims. The trusted-poisoning test deliberately demonstrates that a false duration
with matching owner pins is rendered. Deterministic rendering does not prove that
source facts are authentic, accurate or complete, and does not improve or measure
Qwen resistance. No real authentication/revocation service or production ingestion
adapter has been tested. Direct fact rendering could avoid an unnecessary model
call entirely for this task class.

A later live evaluation would require **fresh explicit approval** after review:
freeze policy/templates, source set, record schemas, independent expected answers
and integrity anchors first; then use new records and independently authored
payloads in exactly eight local Qwen calls (four attacks/four controls), zero
retries, fixed model digest, cloud disabled, no pulls/fallback or paid calls.
Authorize the exact plan hash and budget separately. Include broader unsupported
tasks and withheld source/context checks as offline controls, and independently
review model behavior and final factual completion. No such live plan is executed
or implicitly authorized by this implementation.
