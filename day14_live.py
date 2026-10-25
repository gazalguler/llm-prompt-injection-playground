"""Execute the explicitly approved 30-trial Day 14 plan once, without retries."""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import urllib.request
import urllib.error

from day14_trials import make_plan, prepare, record

CAP = Decimal('0.03')
INPUT = Decimal('0.15') / 1_000_000
OUTPUT = Decimal('0.60') / 1_000_000


def now():
    return datetime.now(timezone.utc).isoformat()


def input_bound(request):
    # UTF-8 bytes upper-bound text tokens; 2048 covers message/tool framing.
    return len(json.dumps(request['messages'], ensure_ascii=False).encode()) + 2048


def key_from(root):
    key = os.environ.get('OPENAI_API_KEY', '')
    if not key:
        text = (root / '.env').read_text(encoding='utf-8-sig')
        match = re.search(r'^\s*(?:export\s+)?OPENAI_API_KEY\s*=\s*(.*?)\s*$', text, re.M)
        key = match.group(1).strip().strip('\"\'') if match else ''
    if not key.startswith('sk-') or any(c.isspace() for c in key):
        raise ValueError('Missing or invalid local API key; value withheld.')
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def send(request, key):
    req = urllib.request.Request('https://api.openai.com/v1/chat/completions',
        data=json.dumps(request).encode(), method='POST',
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=60) as response:
            return response.status, response.headers.get('x-request-id'), response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get('x-request-id'), error.read()


def execute(root, run_id, transport=send):
    key = key_from(root) if transport is send else 'offline-fixture'
    plan = make_plan(run_id, trials=3, seed=14, expanded=False, max_requests=30)
    assert len(plan['requests']) == 30 and plan['max_output_tokens'] == 6000
    ceiling = sum(input_bound(r['request']) * INPUT + 200 * OUTPUT for r in plan['requests'])
    if ceiling > CAP:
        raise ValueError('Plan exceeds approved cap.')
    directory = root / 'day14_runs' / run_id
    # One durable authorization lock per repository: no resume or second run.
    lock = root / 'day14_runs' / 'approved_main_20261025.lock'
    lock.parent.mkdir(exist_ok=True)
    with lock.open('x', encoding='utf-8') as stream:
        json.dump({'run_id': run_id, 'approved_usd': str(CAP), 'started_at': now()}, stream)
    prepare(directory, plan)
    (directory / 'budget.json').write_text(json.dumps({
        'approved_usd': str(CAP), 'conservative_usd': str(ceiling),
        'pricing_date': '2026-10-25', 'input_usd_per_million': '0.15',
        'output_usd_per_million': '0.60',
        'pricing_source': 'https://developers.openai.com/api/docs/models/gpt-4o-mini',
        'input_bound': 'UTF-8 serialized message bytes plus 2048 per request',
        'provider_side_cap': 'not verified; local cap only',
        'authorization': 'User approved 30 requests once, maximum USD 0.03 in chat',
        'retries': 0}, indent=2), encoding='utf-8')
    spent = Decimal(0)
    completed = 0
    status = 'stopped'
    try:
        for index, trial in enumerate(plan['requests'], 1):
            request = trial['request']
            bound = input_bound(request)
            worst = bound * INPUT + 200 * OUTPUT
            if spent + worst > CAP:
                raise ValueError('Remaining budget insufficient.')
            stem = directory / f'http_{index:02d}'
            with (directory / 'execution.jsonl').open('a', encoding='utf-8') as log:
                log.write(json.dumps({'event': 'attempt', 'trial_id': trial['trial_id'],
                    'timestamp': now(), 'input_bound': bound, 'reserved_usd': str(worst)}) + '\n')
                log.flush()
                os.fsync(log.fileno())
            code, request_id, raw = transport(request, key)
            stem.with_suffix('.json').write_bytes(raw)
            meta = {'trial_id': trial['trial_id'], 'timestamp': now(), 'http_status': code,
                'provider_request_id': request_id, 'raw_sha256': hashlib.sha256(raw).hexdigest()}
            stem.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
            if code != 200:
                raise ValueError(f'HTTP {code}; stopped without retry. See saved raw response.')
            data = json.loads(raw)
            usage = data.get('usage', {})
            pt, ct = usage.get('prompt_tokens'), usage.get('completion_tokens')
            if type(pt) is not int or type(ct) is not int or not 0 <= pt <= bound or not 0 <= ct <= 200:
                raise ValueError('Unknown or out-of-bound usage; stopped without retry.')
            spent += pt * INPUT + ct * OUTPUT
            if not data.get('model', '').startswith('gpt-4o-mini'):
                raise ValueError('Unexpected model; stopped.')
            record(directory, trial['trial_id'], stem.with_suffix('.json'))
            completed += 1
            with (directory / 'execution.jsonl').open('a', encoding='utf-8') as log:
                log.write(json.dumps(dict(meta, event='completed', usage=usage, cumulative_usd=str(spent))) + '\n')
            print(f'{completed}/30 recorded; USD {spent}', flush=True)
        status = 'complete'
    except Exception as error:
        # Never render request objects, credentials, or arbitrary exception text.
        print('Stopped: ' + type(error).__name__ + '; inspect saved records. No automatic retry.', flush=True)
    finally:
        summary = {'status': status, 'completed': completed, 'planned': 30,
            'known_usage_usd': str(spent), 'finished_at': now(),
            'unknown_charge_possible': status != 'complete'}
        (directory / 'execution_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-usd', required=True, choices=['0.03'])
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    result = execute(Path(__file__).resolve().parent, args.run_id)
    raise SystemExit(result['status'] != 'complete')
