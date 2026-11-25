from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from day40_benchmark import Config, benchmark, run_batch, summarize, synthetic_inputs


class BenchmarkTests(unittest.TestCase):
    def test_config_defaults_and_bounds(self):
        self.assertEqual(Config().sizes, (10, 100, 500))
        self.assertEqual(Config().workers, (1, 2, 4))
        for overrides in ({'sizes': ()}, {'sizes': (501,)}, {'sizes': (10, 10)},
                          {'sizes': (4, 5, 6, 7)}, {'sizes': (1,)},
                          {'workers': (3,)}, {'workers': (True,)},
                          {'batches': 6}, {'reliability_size': 21}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                Config(**overrides)

    def test_measurements_use_nearest_rank_and_batch_wall_time(self):
        samples = [value * 1_000_000 for value in range(20, 0, -1)]
        self.assertEqual(summarize(samples, 40_000_000), {
            'samples': 20, 'mean_ms': 10.5, 'median_ms': 10.5,
            'p95_ms': 19, 'operations_per_second': 500,
        })
        self.assertEqual(summarize([1_000_000], 2_000_000)['p95_ms'], 1)
        with self.assertRaises(ValueError):
            summarize([], 1)
        with self.assertRaises(ValueError):
            summarize(samples, 0)

    def test_synthetic_inputs_are_repeatable_with_stable_unique_keys(self):
        state, keys = synthetic_inputs(4)
        self.assertEqual((state, keys), synthetic_inputs(4))
        self.assertEqual(keys, tuple(f'benchmark:{index:04d}' for index in range(4)))
        self.assertEqual((state, keys[:2]), synthetic_inputs(2))

    def test_tiny_matrix_excludes_warmup_and_records_samples(self):
        report = benchmark(Config((2,), (2,), 2, 1))
        self.assertEqual(
            [(item['scenario'], item['workers'], item['samples']) for item in report['results']],
            [('delivery', 2, 4), ('delivery', 1, 2), ('retry', 1, 2),
             ('recovery', 1, 2), ('receiver_lock', 1, 2)],
        )
        for item in report['results']:
            self.assertEqual(item['journal_mode'], {'sender': 'delete', 'receiver': 'delete'})

    def test_temp_databases_cleaned_after_success_and_worker_failure(self):
        with TemporaryDirectory() as parent:
            run_batch(2, 2, 'delivery', temp_root=parent)
            self.assertEqual(list(Path(parent).iterdir()), [])
            with patch('day40_benchmark.deliver', side_effect=RuntimeError('worker failed')):
                with self.assertRaisesRegex(RuntimeError, 'worker failed'):
                    run_batch(2, 2, 'delivery', temp_root=parent)
            self.assertEqual(list(Path(parent).iterdir()), [])
