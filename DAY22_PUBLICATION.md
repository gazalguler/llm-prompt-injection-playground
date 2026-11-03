# Day 22 publication preparation

## Findings and scope

Original live: 4/4 compromised attack outputs blocked, 0/4 clean controls
released, 4/4 false blocks, 0/8 safe released completions. Post-hoc offline
correction: 4/4 compromised outputs blocked, 4/4 controls released, 0/4 false
blocks, 4/8 safe released completions. Model resistance remains 0/4.
These are separate phases; correction is not independent validation.

The sanitized package is results/day22-local-qwen-001. It includes all eight
case-level requests/responses, trusted caller facts, original reviews, unchanged
Day21 decisions, original and corrected Day22 decisions, provenance, source/raw
hashes, checksums, a byte-exact frozen original gate and a network-forbidden
offline verifier. Original raw evidence, model inventory, host paths and logs
remain private and ignored. Optional private linkage checks original bytes;
public-only verification reproduces the published evidence and decisions.

## Validation

107/107 offline unittest methods pass, including additional authored paraphrase,
unsupported-correct-paraphrase abstention, adversarial content/relations, socket
prohibition and package mutation checks. These new probes are separate from live
outputs but authored by the same assistant; they are not independently adjudicated
or statistically independent validation. Five mutation scenarios cover stale
checksums plus gate/request/review/summary changes with recomputed checksums.
All historical replay and public-package verifiers pass. Original Day22's 64
manifest-covered files and manifest, and original Day21's 66 payload files plus
manifest remain unchanged. Earlier historical package verification also passes.

A fresh publication-only copy passed all 107 tests, all replay checks and all
three public package verifiers without private archives. The exact 21-file staging
dry-run passed; the index hash was unchanged and no files were staged. The publication scanner covers the explicit candidate allowlist,
private-directory ignore/untracked checks and bounded credential/key/bearer/secret,
personal-path and email patterns; matching values are never printed. This is a
supplementary scan, not an exhaustive security or privacy proof.

The old Day21 whole-checkout verifier still has its documented Historical artifacts
changed mismatch after intentional subsequent edits; its scope is distinct from
archive byte integrity. It has not been weakened or rewritten. GitHub CI has not
run on these uncommitted changes; local validation does not claim remote CI success.
Narrow grammar, known small synthetic cases, post-observation fitting and assistant
review bias remain research limits, not hidden publication successes.

## Exact staging list (not executed)

From the repository root, this lists only the current Day22 publication changes,
including earlier uncommitted Day22 work. No private raw evidence is included.

```sh
git add -- \
  .gitattributes \
  .github/workflows/python-tests.yml \
  DAY22.md \
  DAY22_PUBLICATION.md \
  README.md \
  day21_publication_check.py \
  day22_analysis.py \
  day22_cases.json \
  day22_facts.json \
  day22_gate.py \
  day22_live_regression.json \
  day22_replay.json \
  results/day22-local-qwen-001/REPORT.md \
  results/day22-local-qwen-001/SHA256SUMS.json \
  results/day22-local-qwen-001/evidence.json \
  results/day22-local-qwen-001/original_gate.py \
  results/day22-local-qwen-001/provenance.json \
  results/day22-local-qwen-001/summary.json \
  results/day22-local-qwen-001/verify.py \
  tests/test_day22_gate.py \
  tests/test_day22_publication.py
```

No files staged, committed or pushed. No additional inference performed.
