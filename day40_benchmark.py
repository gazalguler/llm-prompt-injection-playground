"""Bounded, offline timings for the existing SQLite delivery pipeline."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import platform
import sqlite3
from statistics import mean, median
from tempfile import TemporaryDirectory
from threading import Barrier
from time import perf_counter_ns

from day21_gate import Decision
from day24_recovery import Pin, Record, Snapshot, TASK, record_digest
from day25_authorization import Grant, SourcePolicy
from day26_lifecycle import Authority, Lease
from day27_release import State
from day30_outbox import Outbox
from day31_receiver import Receiver
from day32_delivery import Attempt, Fault, OfflineTransport, deliver

RECIPIENT = 'owner:benchmark'
SCENARIOS = {
    'delivery': (Fault.NONE, Attempt('done', ('applied',))),
    'retry': (Fault.TRANSPORT_UNAVAILABLE, Attempt('transport_unavailable')),
    'recovery': (Fault.LOST_ACK, Attempt('ack_lost', ('applied',))),
    'receiver_lock': (Fault.NONE, Attempt('receiver_unconfirmed')),
}


@dataclass(frozen=True)
class Config:
    sizes: tuple[int, ...] = (10, 100, 500)
    workers: tuple[int, ...] = (1, 2, 4)
    batches: int = 3
    reliability_size: int = 10

    def __post_init__(self):
        for values, limit in ((self.sizes, 500), (self.workers, 4)):
            if (type(values) is not tuple or not values
                    or any(type(value) is not int or not 1 <= value <= limit for value in values)
                    or len(set(values)) != len(values)):
                raise ValueError(f'expected unique positive integers up to {limit}')
        if len(self.sizes) > 3:
            raise ValueError('provide at most three queue sizes')
        if any(worker not in (1, 2, 4) for worker in self.workers):
            raise ValueError('worker counts must be 1, 2 or 4')
        if max(self.workers) > min(self.sizes):
            raise ValueError('each worker needs at least one operation')
        for value, limit in ((self.batches, 5), (self.reliability_size, 20)):
            if type(value) is not int or not 1 <= value <= limit:
                raise ValueError(f'expected an integer from 1 to {limit}')


def synthetic_inputs(size):
    record = Record('incident:40', 'owner:synthetic', 1, 7, 995, 23,
                    'cache', 'restart_restored_service')
    pin = Pin(record.record_id, record.source_id, 1, 7, record_digest(record), 'verified:40', True)
    snapshot = Snapshot(RECIPIENT, True, TASK, record.record_id, 1000, 1100, 60,
                        (record,), (pin,))
    grant = Grant(RECIPIENT, TASK, record.record_id, record.source_id, 7,
                  pin.record_sha256, pin.provenance)
    state = State(snapshot, Lease('lease:40', 4, 990, 1040, SourcePolicy((grant,))),
                  Authority(4, ()))
    return state, tuple(f'benchmark:{index:04d}' for index in range(size))


def summarize(samples_ns, elapsed_ns):
    ordered = sorted(samples_ns)
    count = len(ordered)
    if not count or elapsed_ns <= 0:
        raise ValueError('measurements require samples and positive elapsed time')
    rank = (95 * count + 99) // 100
    return {
        'samples': count,
        'mean_ms': mean(ordered) / 1e6,
        'median_ms': median(ordered) / 1e6,
        'p95_ms': ordered[rank - 1] / 1e6,
        'operations_per_second': count * 1e9 / elapsed_ns,
    }


def run_batch(size, workers, scenario, *, temp_root=None):
    state, keys = synthetic_inputs(size)
    fault, expected = SCENARIOS[scenario]
    with TemporaryDirectory(prefix='day40-', dir=temp_root) as directory:
        sender = Path(directory) / 'sender.sqlite'
        target = Path(directory) / 'receiver.sqlite'
        Outbox.provision(sender)
        Receiver.provision(target)

        def open_workers():
            return Outbox(state, sender), Receiver(target, recipient=RECIPIENT, task=TASK)

        box, _ = open_workers()
        for key in keys:
            if not box.enqueue(key, box.prepare(), 'synthetic candidate',
                               original=Decision(False, None, ('blocked',)), now=1000):
                raise RuntimeError(f'enqueue failed for {key}')

        def attempt(box, receiver, key, now, fault=Fault.NONE):
            return deliver(box, receiver, key, recipient=RECIPIENT, task=TASK,
                           now=now, transport=OfflineTransport(fault))

        def process(box, receiver, key):
            start = perf_counter_ns()
            if scenario == 'receiver_lock':
                with closing(sqlite3.connect(target)) as lock:
                    lock.execute('BEGIN IMMEDIATE')
                    first = attempt(box, receiver, key, 1001, fault)
                    lock.rollback()
            else:
                first = attempt(box, receiver, key, 1001, fault)
            if first != expected:
                raise RuntimeError(f'{scenario} {key}: expected {expected}, got {first}')
            if scenario != 'delivery':
                if scenario == 'recovery':
                    box, receiver = open_workers()
                result = attempt(box, receiver, key, 1006)
                receipt = 'duplicate' if scenario == 'recovery' else 'applied'
                if result != Attempt('done', (receipt,)):
                    raise RuntimeError(f'{scenario} {key}: retry returned {result}')
            return perf_counter_ns() - start

        # Capture the wall-clock window at the point the worker group is released.
        window = []

        def start_window():
            window.append(perf_counter_ns())

        gate = Barrier(workers + 1, action=start_window)

        def work(index, box, receiver):
            gate.wait(timeout=10)
            samples = [process(box, receiver, key) for key in keys[index::workers]]
            return samples, perf_counter_ns()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            jobs = [pool.submit(work, index, *open_workers()) for index in range(workers)]
            gate.wait(timeout=10)
            results = [job.result() for job in jobs]
        elapsed = max(end for _, end in results) - window[0]

        with closing(sqlite3.connect(sender)) as db:
            rows = db.execute('SELECT operation_id, status, attempts FROM outbox ORDER BY operation_id').fetchall()
            sender_mode, = db.execute('PRAGMA journal_mode').fetchone()
        with closing(sqlite3.connect(target)) as db:
            receipts = db.execute('SELECT operation_id, payload FROM receipts ORDER BY operation_id').fetchall()
            effects = db.execute('SELECT operation_id, payload FROM effects ORDER BY operation_id').fetchall()
            receiver_mode, = db.execute('PRAGMA journal_mode').fetchone()
        attempts = 1 if scenario == 'delivery' else 2
        if (rows != [(key, 'done', attempts) for key in keys]
                or [key for key, _ in receipts] != list(keys) or receipts != effects):
            raise RuntimeError(f'{scenario}: persisted delivery state did not match workload')
        return [sample for samples, _ in results for sample in samples], elapsed, {
            'sender': sender_mode, 'receiver': receiver_mode,
        }


def benchmark(config):
    cases = [('delivery', size, workers) for size in config.sizes for workers in config.workers]
    cases.extend((scenario, config.reliability_size, 1) for scenario in SCENARIOS)
    # Reuse an identical delivery case when the two matrices overlap.
    results = []
    for scenario, size, workers in dict.fromkeys(cases):
        run_batch(workers, workers, scenario)
        samples, elapsed = [], 0
        for _ in range(config.batches):
            times, batch_elapsed, modes = run_batch(size, workers, scenario)
            samples.extend(times)
            elapsed += batch_elapsed
        results.append({'scenario': scenario, 'queue_size': size, 'workers': workers,
                        'journal_mode': modes, **summarize(samples, elapsed)})
    return {
        'python': platform.python_version(),
        'sqlite': sqlite3.sqlite_version,
        'os': platform.system(),
        'os_version': platform.mac_ver()[0] or platform.release(),
        'architecture': platform.machine(),
        'timing': 'time.perf_counter_ns',
        'warmup': 'One discarded fresh batch per case, one operation per worker',
        'percentile': 'Nearest rank, ceil(0.95 * n) in ascending order, one-based',
        'config': asdict(config),
        'results': results,
    }


def main():
    defaults = Config()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', nargs='+', type=int, default=defaults.sizes)
    parser.add_argument('--workers', nargs='+', type=int, default=defaults.workers)
    parser.add_argument('--batches', type=int, default=defaults.batches)
    parser.add_argument('--reliability-size', type=int, default=defaults.reliability_size)
    args = parser.parse_args()
    try:
        config = Config(tuple(args.sizes), tuple(args.workers), args.batches, args.reliability_size)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(benchmark(config), indent=2))


if __name__ == '__main__':
    main()
