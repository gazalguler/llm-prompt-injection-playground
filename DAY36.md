# Day 36 — Defensive Mutation Testing & Regression Quality

November 21, 2026 (America/Vancouver)

Day 36 tests whether the delivery regression suite catches incorrect reports
about rejected input, unavailable transport and acknowledgement failures.
The baseline was `38509f553f79285de13802e1cecf561bb4b8520a`, verified against
GitHub's `main` before editing.

## Mutations and results

Each row describes one substitution in the return value of
`day32_delivery.deliver`. The runner applies each substitution to a fresh
temporary copy and runs all Day 29–35 test modules, including the replay
ledger, outbox, receiver, crash-recovery and model-based regressions.
The detector column names a test that failed for that mutation. The runner
prints all failing methods.

| Mutation | Exact return value change | Detector in `tests/test_day32_delivery.py` | Before | After |
| --- | --- | --- | --- | --- |
| Invalid transport status | `Attempt('invalid_transport')` → `Attempt('invalid_message')` | `test_invalid_transport_preserves_pending_intent_for_recovery` | Survived | Killed |
| Outage status | `Attempt('transport_unavailable')` → `Attempt('claim_unavailable')` | `test_temporary_transport_failure_then_duplicate_first_delivery` | Killed | Killed |
| Lost acknowledgement status | `Attempt('ack_lost', tuple(results))` → `Attempt('ack_unconfirmed', tuple(results))` | `test_lost_ack_and_duplicate_frames_across_restart` | Killed | Killed |
| Acknowledgement failure results | `Attempt('ack_unconfirmed', tuple(results))` → `Attempt('ack_unconfirmed')` | `test_receiver_rollback_then_sender_ack_failure_then_recovery` | Killed | Killed |

| Suite | Passing control methods | Killed | Survived | Invalid | Unexecuted | Mutation score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Day 35 baseline | 54 | 3 | 1 | 0 | 0 | 3/4 (75%) |
| Day 36 | 55 | 4 | 0 | 0 | 0 | 4/4 (100%) |

The control must pass in an unmodified copy. A complete mutant run with
assertion failures and no errors or skips counts as killed. A passing mutant
run counts as survived. A missing or ambiguous replacement site or an
inconclusive test result is invalid. A timeout or failed control leaves the
affected mutations unexecuted. The score divides killed mutants by killed
plus survived mutants. All four substitutions were non-equivalent because
each changes an observable `Attempt` value for a reachable input.

The new test passes the string value of `Fault.NONE` where the simulator
requires an enum member. It checks the exact rejection status, that the frame
builder was never called, that every column of the pending sender row is
preserved and that both receiver tables stay empty. After reopening both
databases, valid transport completes delivery in one claim and leaves one
receipt and one effect. The existing route and revocation test now compares
the full sender row after each rejected route or key and after rejection of
an expired-lease retry under revoked authority. Restoring authorization
allows that retry to finish with one committed effect.

## Verification

Python 3.13.18 and pytest 9.2.0 were used. Each baseline runner reported
248 passed, five skipped and zero failed across 253 unique methods. The
final unittest and pytest method IDs matched exactly. Each runner reported
249 passed, five skipped and zero failed across 254 unique methods. The five
skips require the private Day 23 raw archive. Pytest also reported 779
passing subtests, which are excluded from the method count.

The Day 13 metrics check, the Day 16–19 and Day 21–24 offline checks, all five
public package verifiers, the publication privacy scan and Git whitespace
checks passed. The runs used synthetic fixtures and local SQLite with no
model or paid API calls.

## Reproduce

From the repository root with Python 3.13 and pytest 9.2.0 available:

```sh
export PYTHONDONTWRITEBYTECODE=1
python -S day36_mutations.py
python -S -m unittest discover -s tests -t . -p 'test_*.py' -v
python -m pytest tests -q -rs -p no:cacheprovider

for script in day13_metrics.py day16_analysis.py day17_analysis.py \
    day18_analysis.py day19_analysis.py day21_analysis.py day22_analysis.py \
    day23_evaluate.py day24_replay.py; do
    python -S "$script" --check || exit 1
done
for package in local-qwen-proposed-001 day21-local-qwen-001 \
    day22-local-qwen-001 day23-local-qwen-001 day24-offline-recovery-001; do
    python -S "results/$package/verify.py" || exit 1
done
python -S day21_publication_check.py
git diff --check
git diff --cached --check
```

To reproduce the baseline mutation results, use the Day 36 runner against a
temporary checkout of the Day 35 tests:

```sh
(
    baseline=$(mktemp -d)
    trap 'rm -rf "$baseline"' EXIT
    git clone --quiet --no-checkout . "$baseline/repo" &&
        git -C "$baseline/repo" checkout --quiet --detach 38509f553f79285de13802e1cecf561bb4b8520a &&
        cp day36_mutations.py "$baseline/repo/" &&
        python -S "$baseline/repo/day36_mutations.py"
)
```

The runner copies tracked top-level and test Python files from the working
tree. It changes one source file per temporary copy, disables bytecode writes
and removes the copies on exit.

## Limits

The score describes four hand-selected result mutations in one offline
adapter. Authorization, recipient binding, idempotency, lease validation
and transaction behavior are outside the mutation set. The regression
assertions exercise some of those protections on the original code. The
experiment covers local SQLite effects, and the public verification can check
only published evidence where original raw archives are private.
