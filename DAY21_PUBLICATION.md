# Day 21 publication-readiness review

## Scope and code review

The local gate, eight-case runner, original-cohort replay, nine Day 21 tests and
the two-test LF/CRLF fix were reviewed. No blocking defect was found for this
narrow experiment. The gate is a trusted-caller, exact sentence allowlist, not
semantic fact verification. Release and attack judgments are separate. The
runner's fixed plan/preflight/reservation/no-retry controls and tests preserve the
eight-call bound; it must not be executed again under the exhausted approval.
`day21_live.py` and `day21_gate.py` remain byte-identical to the run snapshots.

The LF/CRLF change affects only source-fingerprint compatibility for two CSVs.
Changed content, request/raw hashes, decisions and metrics still fail. Original
reports/CSV files and historical OpenAI/Qwen results are untouched.

The publication verifier checks exact source hashes, all eight requests,
case routing, completion, gate decisions and original review projections,
plus independently derived model/gate counts. Optional private-archive linkage
is explicit. It never executes inference and forbids sockets during its checks.
A fresh publication tree without private archives must pass too. Package mutation
checks exercise checksum and semantic verification; they are additional to the
unchanged 87-test regression suite.

## Sanitized results and immutable evidence

See [public report](results/day21-local-qwen-001/REPORT.md). Model resistance 2/6;
malicious outputs blocked 4/4; clean correct outputs released 4/4; false blocks
0/4. Blocking is abstention, not improved resistance or task recovery.
All eight case-level manual judgments and saved gate decisions are preserved.
Response timestamps/performance/token measurements, full local model inventory,
local paths and private logs are excluded from the allowlisted public subset.

The private archive has **66 manifest-covered payload files plus its manifest**.
Original manifest SHA-256:
`35add5106ff5f9a0553dfc78949e09a55ed913700ec5fce0bba3b80367b97f46`.
All original bytes and the old Day 16 failure log are preserved unchanged.

Original `day21_live.py --verify` still fails `Historical artifacts changed`:
it requires full equality with the pre-run checkout inventory, which subsequent
intentional Day 16 code/test and publication/docs/ignore/CI edits no longer meet.
New public result files also change that inventory. This check is not weakened,
patched or bypassed; its expected failure is recorded separately from passing
archive-byte/package checks. The public verifier makes no checkout-equality claim.

## Verification and review limits

Run all 87 offline tests with no real sockets, historical public Qwen verification,
Days 13, 16, 17, 18, 19 and 21 replay checks and the new package verifier.
Repeat tests/replays/package checks in a temporary publication-only tree containing
HEAD plus only the exact files listed below, with no private Day 21/Ollama logs.
Run `day21_publication_check.py` for the explicit file allowlist, ignored/untracked
private-directory checks and bounded secret/path/email patterns. The source of
that scanner defines the rules; it never prints matched secret values.

No installed gitleaks/detect-secrets scanner was available. No tools/dependencies
were downloaded and no network was used for scanning. Pattern checks plus manual
allowlist review are supplementary, not an exhaustive privacy/security proof.
General security conclusions remain blocked by the small known synthetic sample,
development-selected accepted sentences and absence of independent human labels.
New correct paraphrases can be blocked even though these four clean outputs passed.

The workflow is prepared to run the checks on a later push, but no new GitHub CI
run, commit or push has occurred. Local validation does not establish GitHub CI status.

## Completed local publication validation

- Working tree: 87/87 tests passed with real socket creation forbidden.
- Fresh HEAD-plus-22-file publication tree, without private Day 21/Ollama logs:
  87/87 tests passed; Days 13, 16, 17, 18, 19 and 21 replays and both public
  result-package verifiers passed in both trees.
- Five deliberate temporary corruptions were rejected: checksum, recomputed-
  checksum gate change, request change, task-label/metric change and source edit.
- All 22 candidates passed bounded token/private-key/bearer/secret-assignment,
  personal-path and email scanning. Seven synthetic positive fixtures proved
  the scanner rules detect those patterns. No matching values are printed.
- Original live payload (66 files) and its manifest remain byte-identical;
  all previously tracked public result files still equal HEAD bytes.
- The original full-checkout validator was run offline and still failed exactly
  `Historical artifacts changed`, as expected. It was not modified or patched.
- Git staging dry-run listed exactly the 22 allowlisted files. The index hash
  stayed unchanged and there are no staged files.
- Raw-directory ignore checks passed for every existing private file. Exact-byte
  attributes protect the old public package; LF attributes protect the new
  package/current source hashes across checkout styles.

Local detailed validation logs remain ignored in day21_followup_checks; they are
not part of publication. There are no unresolved local publication-preparation
blockers. Remaining qualifications are the explicitly retained original-checkout
validator mismatch, narrow research scope, bounded scanner coverage and GitHub CI
not yet run for these uncommitted changes. User review still precedes commit/push.

## Exact safe staging list (not staged)

The following 22-file command is the complete publication allowlist. It includes
only two existing code/test edits for the LF/CRLF fix, the new Day 21 source/tests,
public documentation/package and supporting ignore/checkout/CI updates:

```sh
git add -- \
  .gitattributes \
  .gitignore \
  .github/workflows/python-tests.yml \
  README.md \
  DAY21.md \
  DAY21_PUBLICATION.md \
  day16_analysis.py \
  tests/test_day16_defense.py \
  day21_gate.py \
  day21_live.py \
  day21_analysis.py \
  day21_replay.json \
  day21_publication_check.py \
  tests/test_day21_gate.py \
  tests/test_day21_live.py \
  results/day21-local-qwen-001/REPORT.md \
  results/day21-local-qwen-001/cases.csv \
  results/day21-local-qwen-001/evidence.json \
  results/day21-local-qwen-001/provenance.json \
  results/day21-local-qwen-001/summary.json \
  results/day21-local-qwen-001/verify.py \
  results/day21-local-qwen-001/SHA256SUMS.json
```

Use `git add --dry-run --` with the same explicit list to review it. Do not use
broad staging or force-add private directories. The read-only
`day21_publication_check.py` keeps this exact list in `STAGING_FILES`.

## Raw-directory protection and staging state

`day21_runs/`, `day21_followup_checks/`, `ollama_runs/` and `day14_runs/` are
ignored and have no tracked files; every existing private file is checked against
ignore rules. Normal `git add .`/`git add -A` excludes them. Explicit `git add -f`
can override ignores, so an absolute impossibility claim would be incorrect.

Historical `day15_runs/` already contains tracked evidence from earlier commits.
Ignore rules do not untrack it. This work does not stage or modify that historical
archive, and it is not on the new staging list. No files have actually been staged.
No additional inference is permitted by this publication-preparation task.
