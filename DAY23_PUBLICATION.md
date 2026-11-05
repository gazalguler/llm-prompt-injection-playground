# Day 23 publication preparation

## Negative evaluation, unchanged evidence

Day 23 does not show a useful successful defense. Model resistance is **0/4**;
full attack success **2/4**, partial compliance **2/4**. The unchanged Day 22 gate
blocks **4/4 compromised attacks**, releases **0/4 paired controls**, falsely blocks
**3/3 clean-correct controls**, and completes **0/8 tasks through safe released
output**. Model behavior, containment, false blocking and task completion remain
separate. The same gate dispositions occur under the limited fixed-contract Day 21
baseline. Original strict factual completion stays **6/8**; core-fact presence is
**7/8**, with the original disclosed review sensitivity retained.

The [sanitized package](results/day23-local-qwen-001/REPORT.md) is a negative-result
publication, not another grammar correction. Its three clean false blocks are
caused by unsupported passive restoration, down/recovered phrasing and the synonym
offline. All trusted facts and independent pins validate, and none of the three
sentences matches an incident grammar production. The separate multilingual
control invents database failure as outage cause and denies specific downtime
details despite the provided duration. It remains contaminated and excluded from
the clean-correct denominator. No output, gate decision or review is relabeled.

The approved plan hash remains
`3243869f050406331742f924445a92a34c3c0a685346e90b4d6c30b1f7a8a0fd`.
The original full live-result hash remains
`4df6f0195f3e1dcfa751057d2c809d1ab596da5f4678f47b4ffa4777dcb9ad94`.
The 51-file run plus manifest and 13-file review supplement plus manifest remain
byte-exact and ignored/untracked. The frozen runner, plan, fixtures, gates,
responses, judgments, original reports and all historical evidence are preserved.

## Package contents and verification scope

The 15-file package contains REPORT.md, evidence.json, summary.json,
provenance.json, plan.json, plan.sha256, run_manifest.json, review_manifest.json,
reviews.json, review_stage.json, rejection_analysis.json, day21_gate.py,
day22_gate.py, verify.py and SHA256SUMS.json.

Public response projections preserve exact assistant content and completion/model
fields while excluding timestamps, token/performance/cache values. Full model
inventory, host paths, environment logs and baseline inventories remain private.
The exact synthetic requests, original review bytes, plan bytes, gate sources and
original manifest bytes are retained. Request fingerprints are canonical JSON
hashes; raw digests reference original private HTTP bytes and are not recomputable
from the sanitized projection alone. No private raw archive is uploaded.

The standard-library verifier works from the package folder alone, with real
sockets forbidden. It reproduces every gate decision, original review association,
metric denominator and clean-control grammar diagnosis. Optional private linkage
checks sealed inventories, original raw responses/attempts/statuses, metadata and
saved decisions. Public-only verification establishes snapshot consistency and
reproduction, not independent execution, source authenticity, review correctness,
binary attestation or cloud/egress audit. Hash anchors are not signatures.

## Validation

The working checkout passes **132 unittest tests** and **132 pytest tests with
330 passed subtests**. Seven new publication tests cover public reproduction,
standalone copying, exact plan/gate/review preservation, three grammar diagnoses,
missing/extra/stale-checksum data, ten mutations with recomputed checksums and
three original-review/manifest-anchor mutations. The existing five private-archive
review tests retain their explicit skip behavior when the archive is absent.

All Day 13 report and Day 16/17/18/19/21/22 historical replay checks, Day 23 frozen
plan/offline report and sealed live-result verification, and all four public
package verifiers pass. Optional private Day 21/22/23 linkages pass without
weakening the old Day 21 whole-checkout verifier's separately documented scope.
The publication scanner covers 68 explicit candidate files and checks private
folders remain ignored and untracked. Its bounded credential/key/bearer/secret,
local-path and email patterns are supplementary checks, not an exhaustive privacy
or security proof. Matching values are never printed.

CI is extended to run the frozen Day 23 offline plan check and the new public
verifier without requiring a model server or private archive. No commit, push or
remote CI execution is claimed. Local publication checks make no network calls.

Run from the repository root with its Python 3.13 environment:

```sh
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py' -v
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
.venv/bin/python -B -S day13_metrics.py --check
.venv/bin/python -B -S day16_analysis.py --check
.venv/bin/python -B -S day17_analysis.py --check
.venv/bin/python -B -S day18_analysis.py --check
.venv/bin/python -B -S day19_analysis.py --check
.venv/bin/python -B -S day21_analysis.py --check
.venv/bin/python -B -S day22_analysis.py --check
.venv/bin/python -B -S day23_evaluate.py --check
.venv/bin/python -B -S day23_review.py --check
.venv/bin/python -B -S results/local-qwen-proposed-001/verify.py
.venv/bin/python -B -S results/day21-local-qwen-001/verify.py
.venv/bin/python -B -S results/day22-local-qwen-001/verify.py
.venv/bin/python -B -S results/day23-local-qwen-001/verify.py
.venv/bin/python -B -S results/day23-local-qwen-001/verify.py --public-only
.venv/bin/python -B -S day21_publication_check.py
```

A fresh public-only copy with no ignored private archives ran all 132 unittest
methods: **127 passed and 5 private-only methods skipped**. Pytest reports
**127 passed, 5 skipped, 321 passed subtests**. All eight public report/replay/plan
checks, all four public-package verifiers and the publication scanner passed in
that copy. Its private-only review methods are reported as skips, not passing
raw-byte checks.
The complete package can be copied alone and verified using
`python -B -S verify.py --public-only`; standalone reproduction is exercised by a
test. Local-only historical-byte verification is separately retained in this checkout.

## Day 24 proposal, not part of Day 23 results

[DAY24_PROPOSAL.md](DAY24_PROPOSAL.md) proposes deterministic owner-controlled
rendering from independently authenticated, authorized, current structured facts.
Model/tool text cannot select facts, routing, revisions or templates. A rejected
candidate is discarded; a distinct authorized recovery policy may render only
explicitly supported relations using typed finite values. Missing/conflicting,
stale or unauthorized records and unsupported user tasks abstain. The proposal
addresses grammar-dependent utility while acknowledging upstream truth and access
control assumptions. It has not been implemented, tested or evaluated here.
Future model resistance, original blocking, recovery eligibility and final task
completion must remain separate metrics under a new frozen evaluation.

## Preservation check

A pre-publication SHA-256 baseline covers 766 existing files. **762 remain
byte-identical**. The only baseline changes are .gitattributes, the offline CI
workflow, README.md and the publication scanner. In particular the approved plan,
original live results, gate sources, review judgments, both Day 23 sealed archives,
Day 21/22 packages and all historical experiment evidence remain unchanged.
No Day 23 historical document was rewritten; the new package is a separate
sanitized projection. Publication validation records are kept in a separately
sealed ignored publication folder, never appended to the original run/review seals.

## Exact publication candidates (not staged)

These include prior uncommitted Day 23 preparation/live work, this publication
package, documentation, tests and narrow repository-infrastructure updates. No
ignored raw evidence is included. No staging, commit or push was performed.

New files (29):

- `DAY23.md`
- `DAY23_LIVE.md`
- `DAY23_PUBLICATION.md`
- `DAY24_PROPOSAL.md`
- `day23_cases.json`
- `day23_evaluate.py`
- `day23_live_results.json`
- `day23_offline.json`
- `day23_plan.json`
- `day23_plan.sha256`
- `day23_review.py`
- `results/day23-local-qwen-001/REPORT.md`
- `results/day23-local-qwen-001/SHA256SUMS.json`
- `results/day23-local-qwen-001/day21_gate.py`
- `results/day23-local-qwen-001/day22_gate.py`
- `results/day23-local-qwen-001/evidence.json`
- `results/day23-local-qwen-001/plan.json`
- `results/day23-local-qwen-001/plan.sha256`
- `results/day23-local-qwen-001/provenance.json`
- `results/day23-local-qwen-001/rejection_analysis.json`
- `results/day23-local-qwen-001/review_manifest.json`
- `results/day23-local-qwen-001/review_stage.json`
- `results/day23-local-qwen-001/reviews.json`
- `results/day23-local-qwen-001/run_manifest.json`
- `results/day23-local-qwen-001/summary.json`
- `results/day23-local-qwen-001/verify.py`
- `tests/test_day23_evaluate.py`
- `tests/test_day23_publication.py`
- `tests/test_day23_review.py`

Modified repository infrastructure (5):

- `.gitattributes`
- `.github/workflows/python-tests.yml`
- `.gitignore`
- `README.md`
- `day21_publication_check.py`
