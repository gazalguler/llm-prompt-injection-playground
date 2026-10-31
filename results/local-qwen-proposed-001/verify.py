"""Offline public-subset verification; never invokes evaluation.run()."""
import csv
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
public = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
import ollama_evaluate as runner

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(value, message):
    if not value:
        raise SystemExit(message)

manifest = json.loads((public / 'SHA256SUMS.json').read_text())
require(set(manifest) == {p.name for p in public.iterdir() if p.is_file()} - {'SHA256SUMS.json'}, 'Unexpected public file set')
for name, digest in manifest.items():
    require(sha(public / name) == digest, 'Public checksum mismatch: ' + name)
provenance = json.loads((public / 'provenance.json').read_text())
for name, digest in provenance['source_sha256'].items():
    require(sha(root / name) == digest, 'Source checksum mismatch: ' + name)
evidence = json.loads((public / 'evidence.json').read_text())
plan = runner.make_plan(provenance['run_id'])
require(len(evidence) == len(plan['requests']) == 16, 'Wrong evidence count')
with (public / 'cases.csv').open(newline='') as stream:
    cases = list(csv.DictReader(stream))
require(len(cases) == 16, 'Wrong case count')
for item, trial, case in zip(evidence, plan['requests'], cases):
    require(item['trial_id'] == trial['trial_id'] == case['trial_id'], 'Trial alignment mismatch')
    require(item['request'] == trial['request'], 'Offline plan mismatch')
    require(runner.fingerprint(item['request']) == item['request_sha256'] == trial['request_sha256'], 'Request hash mismatch')
    for key in ('dataset', 'case_id', 'kind', 'condition'):
        require(case[key] == trial[key], 'Case identity mismatch')
    response = item['response']
    require(item['http_status'] == 200 and response['done'] is True and response['done_reason'] == 'stop', 'Incomplete response')
    require(response['model'] == provenance['model'] and response['message']['role'] == 'assistant', 'Response identity mismatch')
    # Recorded outcomes are human-readable judgments, not inferred from marker presence.
for condition, successes, resisted in [('baseline', 6, 0), ('trust_boundary', 4, 2)]:
    attacks = [c for c in cases if c['condition'] == condition and c['kind'] == 'attack']
    controls = [c for c in cases if c['condition'] == condition and c['kind'] == 'control']
    require(len(attacks) == 6 and len(controls) == 2, 'Wrong denominators')
    require(sum(c['attack_success'] == 'success' for c in attacks) == successes, 'Success count mismatch')
    require(sum(c['attack_success'] == 'resisted' for c in attacks) == resisted, 'Resistance count mismatch')
    require(sum(c['attack_success'] == 'partial' for c in attacks) == 0, 'Partial count mismatch')
    require(sum(c['task_completed'] == 'yes' for c in attacks) == 3, 'Attack task count mismatch')
    require(all(c['task_completed'] == 'yes' and c['attack_success'] == 'not_applicable' for c in controls), 'Control mismatch')
private = root / 'ollama_runs' / provenance['run_id']
if private.exists():
    for name, digest in provenance['source_artifact_sha256'].items():
        require(sha(private / name) == digest, 'Private source mismatch: ' + name)
    for item in evidence:
        raw_path = private / item['source_raw_file']
        require(sha(raw_path) == item['source_raw_sha256'], 'Raw source mismatch')
        raw = json.loads(raw_path.read_text())
        require({key: raw[key] for key in item['response']} == item['response'], 'Response projection mismatch')
        status_path = private / item['source_raw_file'].replace('.raw.json', '.status.json')
        require(sha(status_path) == item['source_status_sha256'], 'Status source mismatch')
    print('Private source linkage verified.')
else:
    print('Private originals absent; their source hashes cannot be independently checked here.')
print('Public checksums, source hashes, exact offline plan, 16 records and reviewed counts verified.')
