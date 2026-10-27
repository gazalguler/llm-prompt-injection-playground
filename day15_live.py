"""Freeze and execute one explicitly authorized Day 15 plan without retries."""
import argparse
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

from day14_live import input_bound, key_from, now, send
from day14_trials import fingerprint, prepare, record
from day15_trials import make_plan, review_template

INPUT = Decimal('0.15') / 1_000_000
OUTPUT = Decimal('0.60') / 1_000_000
SOURCE = 'https://developers.openai.com/api/docs/models/gpt-4o-mini'


def durable(path, data):
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def save(path, value):
    durable(path, (json.dumps(value, indent=2) + '\n').encode())


def journal(directory, value):
    with (directory / 'execution.jsonl').open('ab') as stream:
        stream.write((json.dumps(dict(timestamp=now(), **value)) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def load_plan(directory):
    plan = json.loads((directory / 'plan.json').read_text(encoding='utf-8'))
    # Exact equality validates coverage, prompts, ordering, hashes and all caps.
    if plan != make_plan(plan['run_id']):
        raise ValueError('Plan differs from the frozen default 72-request cohort.')
    return plan


def quote(plan):
    tokens = sum(input_bound(row['request']) for row in plan['requests'])
    return dict(requests=72, model='gpt-4o-mini', input_token_allowance=tokens,
                output_token_allowance=14400,
                conservative_usd=str(tokens * INPUT + 14400 * OUTPUT),
                input_usd_per_million='0.15', output_usd_per_million='0.60',
                pricing_date='2026-10-26', pricing_source=SOURCE,
                input_bound='Serialized UTF-8 message bytes plus 2048 per request',
                provider_side_cap='Not verified; local reservation cap only',
                retries=0, plan_sha256=fingerprint(plan))


def freeze(directory, run_id):
    prepare(directory, make_plan(run_id))
    review_template(directory)
    result = quote(load_plan(directory))
    save(directory / 'quote.json', result)
    return result


def execute(directory, approved_usd, plan_sha256, approval_note, transport=send):
    directory = Path(directory).resolve()
    plan = load_plan(directory)
    estimate = quote(plan)
    cap = Decimal(approved_usd)
    if (not cap.is_finite() or cap <= 0
            or cap < Decimal(estimate['conservative_usd'])
            or plan_sha256 != estimate['plan_sha256'] or not approval_note.strip()):
        raise ValueError('Explicit approval must cover this plan and its full reserve.')
    if json.loads((directory / 'quote.json').read_text()) != estimate:
        raise ValueError('Frozen quote mismatch.')
    if set(p.name for p in directory.iterdir()) != {'plan.json', 'reviews.csv', 'quote.json'}:
        raise ValueError('Execution directory is not pristine; refusing to send.')
    root = Path(__file__).resolve().parent
    key = key_from(root) if transport is send else 'offline-fixture'
    # A cohort-wide exclusive lock prevents a second execution under this approval,
    # even if a caller chooses another run ID. Never delete it to retry a failure.
    lock = directory.parent / 'day15_paid_once.lock'
    save(lock, dict(run_id=plan['run_id'], approved_usd=str(cap),
                    plan_sha256=plan_sha256, approval_note=approval_note,
                    started_at=now()))
    save(directory / 'authorization.json', dict(estimate, approved_usd=str(cap),
                                               approval_note=approval_note))
    reserved = Decimal(0)
    known = Decimal(0)
    attempted = completed = 0
    status = 'stopped'
    try:
        for index, trial in enumerate(plan['requests'], 1):
            request = trial['request']
            bound = input_bound(request)
            worst = bound * INPUT + request['max_tokens'] * OUTPUT
            if attempted >= 72 or reserved + worst > cap:
                raise ValueError('Request or budget cap reached.')
            # Charge the full reserve before sending; never refund unknown charges.
            journal(directory, dict(event='attempt', trial_id=trial['trial_id'],
                    request_sha256=trial['request_sha256'], input_bound=bound,
                    reserved_usd=str(worst), cumulative_reserved_usd=str(reserved + worst)))
            reserved += worst
            attempted += 1
            code, request_id, raw = transport(request, key)
            stem = directory / f'http_{index:02d}'
            durable(stem.with_suffix('.json'), raw)
            meta = dict(trial_id=trial['trial_id'], http_status=code,
                        provider_request_id=request_id,
                        raw_sha256=hashlib.sha256(raw).hexdigest())
            save(stem.with_suffix('.meta.json'), meta)
            journal(directory, dict(meta, event='received'))
            if code != 200:
                raise ValueError('HTTP failure.')
            data = json.loads(raw)
            usage = data.get('usage', {})
            pt, ct = usage.get('prompt_tokens'), usage.get('completion_tokens')
            if (type(pt) is not int or type(ct) is not int
                    or not 0 <= pt <= bound or not 0 <= ct <= 200):
                raise ValueError('Unknown or out-of-bound usage.')
            known += pt * INPUT + ct * OUTPUT
            if data.get('model') not in {'gpt-4o-mini', 'gpt-4o-mini-2024-07-18'}:
                raise ValueError('Unexpected model; no substitution allowed.')
            if not request_id or data['choices'][0].get('finish_reason') not in {'stop', 'length', 'content_filter'}:
                raise ValueError('Missing request ID or unexpected finish reason.')
            record(directory, trial['trial_id'], stem.with_suffix('.json'))
            completed += 1
            journal(directory, dict(event='completed', trial_id=trial['trial_id'],
                                   usage=usage, known_usage_usd=str(known)))
            print(f'{completed}/72 recorded', flush=True)
        status = 'complete'
    except BaseException as error:
        # Never log arbitrary exception messages, headers or credentials.
        journal(directory, dict(event='stopped', error_type=type(error).__name__))
    finally:
        result = dict(status=status, planned=72, attempted=attempted, completed=completed,
                      reserved_usd=str(reserved), known_usage_usd=str(known),
                      unknown_charge_possible=status != 'complete', finished_at=now())
        save(directory / 'execution_summary.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'preflight', 'execute'])
    parser.add_argument('directory', type=Path)
    parser.add_argument('--run-id')
    parser.add_argument('--approved-usd')
    parser.add_argument('--plan-sha256')
    parser.add_argument('--approval-note')
    args = parser.parse_args()
    if args.command == 'prepare':
        if not args.run_id:
            parser.error('prepare requires --run-id')
        result = freeze(args.directory, args.run_id)
    elif args.command == 'preflight':
        result = quote(load_plan(args.directory))
    else:
        if not all([args.approved_usd, args.plan_sha256, args.approval_note]):
            parser.error('execute requires explicit budget, plan hash and approval note')
        result = execute(args.directory, args.approved_usd, args.plan_sha256, args.approval_note)
    print(json.dumps(result, indent=2))
    if args.command == 'execute' and result['status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
