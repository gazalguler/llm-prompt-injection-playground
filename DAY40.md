# Day 40 — Performance benchmarking and reliability profiling

November 25, 2026 (America/Vancouver)

The benchmark drains prefilled SQLite queues through the Day 30 outbox,
Day 31 receiver, and Day 32 offline transport. It exercises authorization,
claim, receiver receipt and effect, and sender acknowledgement through
the existing entry points. Day 39's schema versions (30 and 31) are
provisioned directly. Migration time is outside the measured workload.

## Method

- Each batch provisions a fresh pair of temporary databases and enqueues
  the same synthetic record under deterministic operation IDs. The workers
  share both files. Each thread has its own outbox and receiver instances
  and processes a fixed slice of operation IDs. The workload schedules
  disjoint operations. Fencing tokens and thread scheduling vary naturally.
- The default runs three measured batches per case. Before each case, a
  discarded batch on fresh databases warms up the same path with one
  operation per worker. Setup, enqueue, worker startup, and final database
  checks are outside the measured interval.
- Per-operation latency uses Python's monotonic `time.perf_counter_ns()`
  from the start of processing through the completed attempt or retry.
  Time spent waiting for a worker behind another queued operation is
  outside this interval. Throughput divides completed operations by the
  sum of batch wall-clock times, from barrier release to the last worker's
  finish. Latency samples are pooled across the three batches. The median
  averages the two middle observations for even sample counts. The p95 is
  the nearest rank, `ceil(0.95 × n)`, in ascending order with one-based ranks.
- Each batch checks that all sender rows are done with the expected
  attempt count and that the receiver has one matching receipt and effect
  for each operation ID. An unexpected outcome aborts the run.
- Environment for the recorded run was Python 3.13.18, SQLite 3.54.1,
  macOS 27.2.1 on arm64, with the temporary files on the local data volume.
  Both databases reported `DELETE` journal mode. The delivery transactions
  use `synchronous=FULL` and a 200 ms SQLite connection timeout.

## Healthy delivery

| Initial queue | Workers | Samples | Mean (ms) | Median (ms) | p95 (ms) | Delivered/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 1 | 30 | 1.108 | 1.084 | 1.234 | 901.4 |
| 10 | 2 | 30 | 2.252 | 1.370 | 4.904 | 799.1 |
| 10 | 4 | 30 | 3.802 | 1.267 | 13.081 | 560.0 |
| 100 | 1 | 300 | 1.202 | 1.114 | 1.624 | 831.6 |
| 100 | 2 | 300 | 2.127 | 1.172 | 4.866 | 731.0 |
| 100 | 4 | 300 | 3.571 | 1.162 | 11.618 | 794.5 |
| 500 | 1 | 1500 | 1.448 | 1.386 | 1.758 | 690.4 |
| 500 | 2 | 1500 | 2.581 | 1.554 | 5.219 | 704.7 |
| 500 | 4 | 1500 | 5.135 | 2.707 | 11.649 | 703.1 |

## Retry, recovery, and contention

Each case uses a queue of 10 and one worker. Transport failure leaves a
sender lease without a receiver write. Lost acknowledgement leaves a
committed receiver effect, then fresh worker objects reopen the same
database paths and confirm the duplicate. In the lock case, a separate
connection holds a receiver `BEGIN IMMEDIATE` through the first attempt.
The timed path includes acquiring and releasing that lock. The sender
claims the operation while the receiver waits for its writer lock and
returns unconfirmed. Each retry starts at synthetic time 1006, exactly
one lease duration after the first attempt at 1001. The logical clock
advances instantly.

| Path | Samples | Mean (ms) | Median (ms) | p95 (ms) | Delivered/s | Mean difference vs. healthy (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Healthy delivery | 30 | 1.108 | 1.084 | 1.234 | 901.4 | +0.000 |
| Transport unavailable, then retry | 30 | 1.431 | 1.419 | 1.615 | 698.0 | +0.323 |
| Lost ack, then reopen and reconcile | 30 | 1.570 | 1.517 | 2.047 | 636.3 | +0.462 |
| Receiver writer lock, then retry | 30 | 238.127 | 238.663 | 243.915 | 4.2 | +237.019 |

## Observations and limits

At 500 operations, throughput ranged from 690 to 705 deliveries per
second across the worker counts, while p95 rose from 1.76 ms with one
worker to 11.65 ms with four. Each healthy delivery opens connections and
takes three write transactions across the two files. Writes serialize
within each file, and the transactions perform schema and integrity checks
while holding the writer reservation. Those costs are plausible contributors
to the higher tail latency and the increase in one-worker latency as the
tables grow. This benchmark does not time individual SQL statements, so
their relative costs are unknown.

The held receiver writer dominated its scenario, adding about 237 ms to
mean latency on this host. The configured busy timeout governs SQLite's
wait budget. The measured interval also includes lock setup, a failed
attempt, scheduling, and successful delivery after release. Transport retry
and lost-ack reconciliation added about 0.32 ms and 0.46 ms respectively
to the healthy mean, with lease waiting excluded.

These are observations from one invocation on one host. Small queues have
only 30 samples per cell, making p95 sensitive to a few observations.
Static slices can leave workers idle near batch end. The run uses one
small payload, fresh databases, and local effects. It omits network and
inference calls, process startup during recovery, physical lease waiting,
and migration. The measurements characterize this offline workload.

## Verification

The Day 39 checkout collected 279 test methods. Day 40 adds five methods
covering bounds, summary calculations, deterministic inputs, warmup
exclusion, and cleanup after success and failure. Unittest and pytest
collected the same 284 method IDs and each reported 279 passed, five
skipped, and zero failed. The skips require the private Day 23 raw archive.
The historical integrity checks, five public package verifiers,
publication privacy scan, and whitespace checks passed. The Day 36 suite
detected all four mutations.

## Reproduce

Run from the repository root. The benchmark requires only the Python
standard library and writes its JSON report to stdout.

```sh
PYTHONDONTWRITEBYTECODE=1 python -S day40_benchmark.py --sizes 10 100 500 \
    --workers 1 2 4 --batches 3 --reliability-size 10
PYTHONDONTWRITEBYTECODE=1 python -S -m unittest tests.test_day40_benchmark
```
