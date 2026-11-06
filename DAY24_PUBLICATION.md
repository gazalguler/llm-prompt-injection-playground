# Day 24 publication preparation

2026-11-06 (America/Vancouver). Prepared on `main` at `1242e20`.
**No staging, commit, push, new inference, server preflight or paid calls.**

## Review conclusion and evidence boundary

The implementation and offline outcomes reproduce: 8/8 correct deterministic
summaries, 0/8 incorrect releases; 34/34 new authored scenarios match expected
outcomes, comprising 9 completions and 25 abstentions. Review found no change
needed to the Day 24 renderer, replay, fixtures or frozen offline report.
The package adds an independent owner-record comparison against the original
Day 23 caller plan and checks every original review/gate disposition.

Original Qwen resistance remains **0/4**, full attack success 2/4 and partial
compliance 2/4. Original gate containment remains 4/4 compromised attacks blocked,
3/3 clean-correct false blocks and 0/8 safe released completion. New deterministic
recovery is a separate system mechanism. Neither candidate repair nor a new model
experiment is claimed. The invented-cause control retains its original negative
judgment while its new summary uses only 92 minutes and database restart.

**Authenticated real-world source integration is outside this experiment.**
The owner adapter, authentication and authorization flags, provenance references,
clock and grant expiry are simulated fixtures. Production authentication,
complete current source selection, task authorization, trusted time and delivery
lease remain external prerequisites. Matching identifiers/digests do not establish
source truth or authenticity. Trusted poisoning, same-author expectations,
observed-failure development replay and finite task/schema all limit the claims.
New authored cases are not independently held-out validation. No model resistance
improvement, production false-release rate or real authentication is established.

## Sanitized public package

`results/day24-offline-recovery-001/` contains exactly **32 files**:
REPORT, case evidence, provenance, separate-denominator summary, verifier and
checksum manifest plus 26 frozen dependency files. The snapshot preserves exact
Day 24 implementation/fixtures/replay/test bytes, original caller plan/results,
required gates and the complete unchanged 15-file sanitized Day 23 package.
There are no private raw archives, local host paths, environment logs, credentials
or new model outputs. Synthetic adversarial payloads remain explicit study data.

The standalone verifier checks the exact recursive file inventory, checksums,
embedded frozen-source anchors, original Day 23 package, replay reproduction,
owner/plan factual agreement, all case-level projections and independently derived
publication metrics. Extra, missing, duplicated or mutated case data fail.
The eight new publication tests exercise standalone operation, repository linkage,
manifest/inventory edits, five source/fixture mutations, eight case-evidence
mutations, four summary/provenance mutations, original bytes and plan binding.
Recomputed manifests cannot hide those mutations. Checksums/anchors are not
signatures: an adversary replacing the verifier and every anchor can replace the
package. Public-only checks cannot attest historical private raw bytes, server
metadata, egress or independent review correctness.

Run from the repository root (existing Python 3.13 environment):

```sh
.venv/bin/python -B -S results/day24-offline-recovery-001/verify.py
.venv/bin/python -B -S results/day24-offline-recovery-001/verify.py --public-only
```

Or copy only that directory and run `python -B -S verify.py --public-only`.
No repository, model server, API keys, third-party libraries or private evidence
are required. Repository mode additionally compares current exact source bytes
and invokes the unchanged Day 23 verifier for available private linkage checks.
The replay/verifier CLI paths forbid sockets and subprocess bytecode writes.

## Validation and preservation

- Full checkout: **158 unittest methods passed**, **158 pytest tests and 465
  subtests passed** (150 existing methods plus eight new publication methods).
- Public-only checkout without ignored private archives: unittest ran 158 methods,
  **153 passed and 5 private-only methods skipped**; pytest **153 passed,
  5 skipped and 456 passed subtests**. Skips do not attest unavailable raw bytes.
- Day 13 metric/dashboard check; Days 16/17/18/19/21/22 historical replay checks;
  Day 23 frozen plan/offline and sealed live review; Day 24 replay all pass.
- All **five** public-package verifiers pass in the full and public-only copies.
  Standalone Day 24 copying/reproduction passes; available original private
  archive linkage checks pass in the full checkout.
- A pre-publication exact-byte baseline covers **799 existing files**, including
  unstaged Day 24 work and existing sealed archives. **795 remain byte-identical**.
  Only `.gitattributes`, the CI workflow, README and publication scanner changed.
  Historical sources, Day 23 proposal/results, all previous public packages,
  frozen plans/reviews and sealed run/review archives remain byte-exact.
- Publication scanner covers **109 explicit candidate files** with no bounded
  credential/key/bearer, personal-path or email-pattern findings. Private folders
  remain ignored and untracked. This is supplementary scanning, not an exhaustive
  privacy/security proof. `git diff --check` passes and the index remains empty.

CI adds the Day 24 offline replay and publication verifier. No network-dependent
model execution is added. These are local validation results; no new remote
GitHub Actions run is claimed.

## Exact safe Git review and optional staging recipe

There are **45 changed/new files: 41 new and four modified**, including the
previously reviewed Day 24 implementation. The list below names every file,
including each nested package file. No ignored evidence folder is selected.
These commands are provided for user review; they have **not** been executed.
Run from the existing repository root. First confirm branch/status and review:

```sh
git branch --show-current
git status --short
git diff --check
git diff -- .gitattributes .github/workflows/python-tests.yml README.md day21_publication_check.py
.venv/bin/python -B -S day21_publication_check.py
.venv/bin/python -B -S results/day24-offline-recovery-001/verify.py
```

After reviewing the implementation, public evidence and all 45 files, the exact
optional staging command is:

```sh
git add -- \
  .gitattributes \
  .github/workflows/python-tests.yml \
  DAY24.md \
  DAY24_PUBLICATION.md \
  README.md \
  day21_publication_check.py \
  day24_cases.json \
  day24_offline.json \
  day24_owner_fixtures.json \
  day24_recovery.py \
  day24_replay.py \
  results/day24-offline-recovery-001/REPORT.md \
  results/day24-offline-recovery-001/SHA256SUMS.json \
  results/day24-offline-recovery-001/evidence.json \
  results/day24-offline-recovery-001/provenance.json \
  results/day24-offline-recovery-001/snapshot/day21_gate.py \
  results/day24-offline-recovery-001/snapshot/day22_gate.py \
  results/day24-offline-recovery-001/snapshot/day23_live_results.json \
  results/day24-offline-recovery-001/snapshot/day23_plan.json \
  results/day24-offline-recovery-001/snapshot/day23_plan.sha256 \
  results/day24-offline-recovery-001/snapshot/day24_cases.json \
  results/day24-offline-recovery-001/snapshot/day24_offline.json \
  results/day24-offline-recovery-001/snapshot/day24_owner_fixtures.json \
  results/day24-offline-recovery-001/snapshot/day24_recovery.py \
  results/day24-offline-recovery-001/snapshot/day24_replay.py \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/REPORT.md \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/SHA256SUMS.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/day21_gate.py \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/day22_gate.py \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/evidence.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/plan.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/plan.sha256 \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/provenance.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/rejection_analysis.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/review_manifest.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/review_stage.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/reviews.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/run_manifest.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/summary.json \
  results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/verify.py \
  results/day24-offline-recovery-001/snapshot/tests/test_day24_recovery.py \
  results/day24-offline-recovery-001/summary.json \
  results/day24-offline-recovery-001/verify.py \
  tests/test_day24_publication.py \
  tests/test_day24_recovery.py
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only | wc -l
git status --short
```

Expected staged count is **45** for this prepared state. Inspect the staged diff
before choosing to commit. No broad directory, wildcard, force-add, commit or
push command was executed. Commit/push remain a separate user review step.
Future inference also requires fresh explicit approval of a separately frozen
bounded plan; preparation or publication is not consent to model execution.
