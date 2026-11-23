# Day 37 — Contract Testing & Interface Compatibility

November 22, 2026 (America/Vancouver)

Day 37 started from `678c9c60541854916008237211d1788ddcc2ad8a`, verified
against GitHub's `main`. The tests exercise the Python interfaces and the
two SQLite databases used by Days 30–36.

## Interfaces examined

| Boundary | Existing contract |
| --- | --- |
| Sender → outbox | `enqueue` stores the authorized rendered text and its context under a stable string operation ID. `claim` revalidates current authority and the recipient/task before committing a lease. It returns a `Claim(operation_id, token, outcome)` or `None`. |
| Outbox → offline transport | `deliver` passes a `Message` to `frames`. The transport supplies a `Fault` member and returns a tuple. An empty tuple indicates unavailability. Every frame must be a `Message` that matches the operation ID, lease token, recipient, task and exact rendered text before any frame reaches the receiver. |
| Sender → receiver | `receive` takes the original claim plus recipient and task. It returns `applied` after committing both rows, `duplicate` for the same stored binding and effect, or `None` on rejection or uncertainty. The receiver binds the operation ID to recipient, task and payload. A subsequent lease can use a different token. |
| Receiver → sender acknowledgement | `dispatch` and `deliver` acknowledge only recognized receipt results. `ack` uses the operation ID, token, current status and lease time to fence stale acknowledgements. `deliver` exposes the attempt status and any confirmed receiver results. |
| Storage → recovery | The outbox checks SQLite version 30 and the stored `outbox` table definition. The receiver checks version 31 and its `receipts` and `effects` definitions. Both run SQLite integrity checks, and the receiver checks foreign keys. Reopened workers reuse the same databases with current trusted state and a caller-supplied time. |

## Regressions and fixes

Seven new methods cover missing transport members, unexpected frame containers,
a frame missing its payload, an invalid token type, and mismatched operation,
recipient, task or payload. Several cases put a valid frame first so the tests
can detect partial delivery. The tests check which fields in the sender row
remain unchanged, whether a lease is consumed, and whether either receiver
table gains a row. Reopened workers verify retry behavior at lease expiry.
The compatibility test changes the outbox version and the receiver table
definition in temporary databases and verifies recovery after restoring the
expected version and definition.

The original implementation failed five of the seven methods. The fixes are
limited to existing input and result checks.

- An unknown stored status could be treated as claimable. Only `pending` and
  eligible `leased` rows may now be claimed.
- SQLite could match an integer acknowledgement operation ID to a numeric
  string key. The outbox now checks the ID and token types before running SQL.
- A truthy release flag such as the string `'false'` could commit a receiver
  effect. The receiver now requires the boolean `True`.
- Day 31 `dispatch` could acknowledge any non-None response. Both send paths
  now use the same check for the two documented success strings and reject
  other types, including string subclasses.
- A transport missing `fault` or a callable `frames` could raise an attribute
  or call error. The adapter now reports `invalid_transport` before claiming.

## Verification

Python 3.13.18 and pytest 9.2.0 ran the same 261 unique methods. Each runner
reported 256 passed, five skipped and zero failed. The skips require the
private Day 23 raw archive. Counts exclude subtests and are reported once
across both runners.

The Day 13 metrics check, Day 16–19 and Day 21–24 offline checks, all five
public package verifiers and publication privacy scan passed. The tests used
temporary SQLite databases and synthetic fixtures. Historical evidence was
preserved. No model or paid API calls were made.

## Reproduce

Run from the repository root with Python 3.13 and pytest 9.2.0.

```sh
set -e
export PYTHONDONTWRITEBYTECODE=1
python -S -m unittest tests.test_day37_contracts -v
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
python -S day21_publication_check.py
git diff --check
git diff --cached --check
```

## Limits

Compatibility here means the existing Python objects and exact versioned
SQLite table definitions. There is no wire format or migration path in this
implementation. Recovery depends on a trusted caller, fresh authority and a
trusted clock. The sender and receiver commit independently, and the receiver
deduplicates only its local SQLite effect. Custom transport exceptions and
external delivery are outside this simulation. Public package checks cannot
verify the private archive bytes that were unavailable to this checkout.
