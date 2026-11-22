"""Run a fixed set of offline delivery result mutations in temporary copies."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent
MODULES = (
    'test_day29_persistence', 'test_day30_outbox', 'test_day31_receiver',
    'test_day32_delivery', 'test_day33_recovery', 'test_day34_recovery_model',
    'test_day35_randomized_recovery',
)
# Each replacement changes only the returned diagnostic, after the same checks
# and database operations. These are distinct, observable Attempt values.
MUTATIONS = (
    ('invalid-transport-status', "Attempt('invalid_transport')",
     "Attempt('invalid_message')"),
    ('outage-status', "Attempt('transport_unavailable')",
     "Attempt('claim_unavailable')"),
    ('lost-ack-status', "Attempt('ack_lost', tuple(results))",
     "Attempt('ack_unconfirmed', tuple(results))"),
    ('ack-failure-results', "Attempt('ack_unconfirmed', tuple(results))",
     "Attempt('ack_unconfirmed')"),
)


def run_tests(directory):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for key in ('PYTHONPATH', 'DAY35_SEED'):
        env.pop(key, None)
    return subprocess.run(
        [sys.executable, '-S', '-m', 'unittest', '-v',
         *(f'tests.{module}' for module in MODULES)],
        cwd=directory, env=env, capture_output=True, text=True, timeout=120,
    )


def main():
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT)
    paths = [Path(os.fsdecode(path)) for path in tracked.split(b'\0') if path]
    paths = [p for p in paths if p.suffix == '.py' and p.parent in (Path('.'), Path('tests'))]
    with TemporaryDirectory(prefix='day36-') as temporary:
        baseline = Path(temporary) / 'baseline'
        for path in paths:
            target = baseline / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        try:
            control = run_tests(baseline)
        except subprocess.TimeoutExpired:
            print('unexecuted: all mutations (control timed out)')
            return 2
        count = re.search(r'^Ran (\d+) tests? ', control.stderr, re.MULTILINE)
        if control.returncode != 0 or not count or not re.search(r'^OK$', control.stderr, re.MULTILINE):
            print(control.stdout + control.stderr)
            print('unexecuted: all mutations (control did not pass without skips)')
            return 2
        print(f'Control: {count[1]} passing Day 29–35 test methods')

        source = (baseline / 'day32_delivery.py').read_text(encoding='utf-8')
        totals = dict.fromkeys(('killed', 'survived', 'invalid', 'unexecuted'), 0)
        for name, before, after in MUTATIONS:
            if source.count(before) != 1:
                status = 'invalid'
                print(f'{name}: {status} (replacement site is missing or ambiguous)')
            else:
                directory = Path(temporary) / name
                shutil.copytree(baseline, directory)
                (directory / 'day32_delivery.py').write_text(
                    source.replace(before, after, 1), encoding='utf-8',
                )
                try:
                    result = run_tests(directory)
                except subprocess.TimeoutExpired:
                    status = 'unexecuted'
                    print(f'{name}: {status} (test run timed out)')
                else:
                    output = result.stderr
                    failures = re.findall(r'^FAIL: (.+)$', output, re.MULTILINE)
                    complete = re.search(rf'^Ran {count[1]} tests? ', output, re.MULTILINE)
                    if complete and result.returncode == 0 and re.search(r'^OK$', output, re.MULTILINE):
                        status = 'survived'
                    elif (complete and result.returncode == 1 and failures
                          and re.search(r'^FAILED \(failures=\d+\)$', output, re.MULTILINE)):
                        status = 'killed'
                    else:
                        status = 'invalid'
                        print(result.stdout + output)
                    print(f'{name}: {status}')
                    for test in dict.fromkeys(failure.split(') (')[0] for failure in failures):
                        print(f'  {test.removesuffix(")")})')
            totals[status] += 1

    print(', '.join(f'{status}={total}' for status, total in totals.items()))
    valid = totals['killed'] + totals['survived']
    if valid:
        print(f"Mutation score: {totals['killed']}/{valid} ({totals['killed'] / valid:.0%})")
    return 2 if totals['invalid'] or totals['unexecuted'] else 0


if __name__ == '__main__':
    sys.exit(main())
