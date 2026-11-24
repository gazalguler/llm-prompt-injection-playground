# Day 39 — Coordinated database migration and crash recovery

November 24, 2026 (America/Vancouver)

Day 39 started from GitHub `main` at
`88aacaed95967a65bb457839a5219f28fd0ab023`. The sender and receiver
can upgrade independently. This change adds regression tests and uses the
existing migration and delivery code.

## Architecture

The Day 30 outbox owns authorization context, delivery leases, and
acknowledgments. The Day 31 receiver owns receipts and effects. Day 32
passes an authorized claim to the receiver and acknowledges it only after
the receiver confirms an applied effect or an exact duplicate. The Day 29
replay ledger is a separate store outside this delivery path. Days 33–37
exercise delivery recovery and its contracts without introducing a shared
database schema.

Day 38's synthetic versions 1 and 2 each differ from their respective
current versions (30 and 31) by one column name. Each migration checks
its own version, schema, integrity, and foreign keys and commits the
rename and version stamp in one SQLite transaction. The operation ID,
recipient, task, and payload carried by a claim keep the same meaning
through either upgrade. This design needs neither a shared version nor a
migration coordinator. Sender and receiver commits are separate SQLite
transactions in separate files.

## Recovery scenarios

- A child process exits immediately before or after committing the first
  upgrade, with each database tested as the first to upgrade. Tests reopen
  both workers, attempt delivery in the resulting state, and explicitly
  retry each migration. A retry upgrades a legacy file or validates an
  already-current file without changing its rows.
- A legacy sender cannot issue a new claim. A current sender can acquire
  a lease while the receiver remains on its legacy schema. The receiver
  withholds confirmation, so the lease remains open until expiry and the
  attempt counts toward the retry limit. Once both stores are current, a
  retry confirms the original receipt as a duplicate and records the
  acknowledgment without applying a second effect.
- A current receiver can confirm an already-issued claim while the sender
  uses its legacy schema. It still rejects the wrong recipient and a
  conflicting payload. The sender can acknowledge the claim once it is
  current again, provided the lease is still valid.
- An unsupported receiver version blocks confirmation and its migration.
  A conflicting effect payload survives the column rename and blocks
  duplicate confirmation. Both cases leave the sender leased and preserve
  the receiver rows.
- A held receiver writer transaction blocks its migration and delivery
  confirmation while the sender upgrade succeeds. Releasing the lock lets
  the receiver upgrade and the sender finish after lease expiry.

## Results

| Checkout | Unique test methods | Passed | Skipped | Failed |
| --- | ---: | ---: | ---: | ---: |
| Day 38 baseline | 274 | 269 | 5 | 0 |
| Day 39 | 279 | 274 | 5 | 0 |

Unittest and pytest each produced those counts using Python 3.13.18,
SQLite 3.54.1, and pytest 9.2.0. Day 39 adds five methods. The two
runners collected the same 279 method IDs. Each method counts once,
including methods with multiple subtests. The five skips require the
private Day 23 raw archive.

The Day 13 metrics, historical replay and integrity checks, all five
public package verifiers, publication privacy checks, and Git whitespace
checks passed. The Day 36 suite detected all four temporary mutations.
No model, cloud inference, or paid API calls were made.

## Reproduce

Run from the repository root with Python 3.13 and pytest 9.2.0.

```sh
set -e
export PYTHONDONTWRITEBYTECODE=1
python -S -m unittest tests.test_day39_independent_migrations -v
python -S -m unittest discover -s tests -t . -p 'test_*.py' -v
python -m pytest tests -q -rs -p no:cacheprovider

for script in day13_metrics.py day16_analysis.py day17_analysis.py \
    day18_analysis.py day19_analysis.py day21_analysis.py day22_analysis.py \
    day23_evaluate.py day24_replay.py; do
    python -S "$script" --check
done
for package in local-qwen-proposed-001 day21-local-qwen-001 \
    day22-local-qwen-001 day23-local-qwen-001 day24-offline-recovery-001; do
    python -S "results/$package/verify.py"
done
python -S day36_mutations.py
python -S day21_publication_check.py
git diff --check
git diff --cached --check
```

The publication script uses a fixed historical allowlist and runs as
shown on a clean checkout. Before staging, the local scan included the
three Day 39 files in that allowlist for the duration of the check.

## Limits

The migration tests use synthetic source schemas and local SQLite
rollback journals. Process exits exercise recovery on the test filesystem.
Power loss, storage failure, automatic rollout, and semantic repair of
existing records are outside the tested scope. A prolonged receiver
outage can exhaust the sender's configured retry budget. The public
package checks cannot verify linkage to the absent private archive bytes.
