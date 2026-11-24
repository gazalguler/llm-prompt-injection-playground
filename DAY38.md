# Day 38 — SQLite schema migration and backward compatibility

November 23, 2026 (America/Vancouver)

Day 38 started from `2f3e66b778d5be6de9e76f9dc75112435ed93d7b`, verified
against GitHub's `main`. The repository history contains three SQLite stores.
Each was introduced with the table definitions it still uses.

| Store | Version | Data and runtime checks |
| --- | --- | --- |
| Day 29 replay ledger | 29 | `claims` binds an operation ID to its authorization binding. Opening it for a claim checks the version, exact table definition and SQLite quick integrity. |
| Day 30 sender | 30 | `outbox` stores the operation ID, serialized authorization context, rendered text, status, lease token and times, and attempt count. Each transaction checks the version, exact table definition and SQLite quick integrity. |
| Day 31 receiver | 31 | `receipts` binds the operation ID to recipient, task and payload. `effects` records the payload with a foreign key to the receipt. Each transaction checks the version, exact table definitions, SQLite quick integrity and foreign keys. |

Days 32–37 reuse the sender and receiver schemas. The version numbers identify
different stores. No historical predecessor of either delivery schema appeared
in the repository history.

## Migration design

`day38_migration.migrate_outbox(path)` and `migrate_receiver(path)` explicitly
upgrade fixture databases. The synthetic sender uses version 1 and names its
payload column `rendered_text`. The synthetic receiver uses version 2 and
names the effect payload column `effect_payload`. The tests create both
fixtures in temporary directories from records written through the existing
delivery interfaces. These version numbers and column names were introduced
for this exercise.

The migrator opens an existing file read-write, enables foreign key enforcement
and sets full synchronous writes. It acquires a writer reservation with
`BEGIN IMMEDIATE` before checking the journal mode, version, exact schema
definitions, database integrity and foreign keys. It requires DELETE
rollback-journal mode, the mode used by the existing stores. It renames one
column in place, sets the target version, and checks the target schema and
integrity in the same transaction. There is no row copy or payload rewrite.
The function returns `True` after commit and `False` for an already-current
file that passes validation. Errors surface as exceptions, and the
transaction rolls back if execution fails before commit.

Normal worker calls still require their current schema versions. The migrator
does not participate in sender authorization, receiver identity checks,
replay claims, or acknowledgement decisions.

## Regression results

- Complete row and schema comparisons covered operation IDs, sender context
  and payload, receiver recipient and task, receipts and effects, and sender
  state for pending jobs, active leases and completed acknowledgements.
- Reopened workers rejected the wrong recipient and conflicting payload,
  honored lease expiry, fenced a stale acknowledgment, deduplicated an effect
  committed before the sender acknowledged it, and processed a pending job.
- A repeated migration preserved the current schema and all rows. The
  migrator rejected missing files, unsupported versions, malformed
  definitions, extra schema objects, a foreign key violation, WAL mode and a
  concurrent writer. The Day 29 ledger retained its replay and binding checks.
- A forced error after the rename and version change restored the source
  schema, version and rows. Separate processes exited immediately before
  commit and after the migration returned. Reopening recovered the full
  source state in the first case and the full target state in the second.

Python 3.13.18, SQLite 3.54.1 and pytest 9.2.0 ran 274 unique test methods,
including 13 added for Day 38. Unittest and pytest each reported 269 passed,
five skipped and zero failed. The five skips require the private Day 23 raw
archive. Each method is counted once across both runners, including methods
that exercise several cases as subtests.

The Day 13 metrics check, Days 16–19 and 21–24 historical replay and integrity
checks, all five public package verifiers, the publication privacy scan,
the Day 36 mutation suite and Git whitespace checks passed locally. The
mutation suite detected all four temporary changes. No OpenAI, Ollama, cloud
inference or paid API calls were made.

## Reproduce

Run from the repository root with Python 3.13 and pytest 9.2.0.

```sh
set -e
export PYTHONDONTWRITEBYTECODE=1
python -S -m unittest tests.test_day38_migration -v
python -S -m unittest discover -s tests -t . -p 'test_*.py' -v
python -m pytest tests -q -rs -p no:cacheprovider
python -S day36_mutations.py

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

The migration covers only the two exact synthetic source schemas and works
on one database at a time. It rejects WAL and custom schema objects. SQLite
integrity and foreign key checks do not establish the provenance or semantic
validity of existing records. Delivery still uses separate sender and receiver
commits with a trusted caller, trusted storage and a trusted clock. Process
exit tests cover SQLite recovery on the test filesystem. Power loss, disk
failure and cross-file atomicity are outside their scope. The public verifiers
cannot independently check the absent private archive bytes.
