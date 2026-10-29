# Day 17: Recovery & Safe Answer Generation

2026-10-28 (America/Vancouver). Parent: `e7abc3c`. Offline only.

## Recovery contract

Day 16 withheld three fact-redefinition responses under the trust-boundary
condition. Day 17 adds a deterministic replacement after rejection. It does not
ask a model to repair its own answer. The rejected text contributes only gate
reasons; its words are never inserted into the replacement.

`day17_recovery.py` defines an immutable, owner-controlled record for the single
synthetic incident: 15 minutes unavailable, service restored by a database
restart. I checked these values against `day15_cases.FACTS` and the preserved
requests. This is a manually reviewed task fixture, not independently verified
production telemetry. No tool text or model claim is promoted into this record.
The caller must provide it through a trusted application path. The Python type
and value checks validate this fixed contract; they do not authenticate a caller
or turn an attacker-supplied matching object into trusted evidence.

The flow is:

1. Apply the unchanged Day 16 gate.
2. Preserve accepted candidates as before.
3. For rejected candidates, require the exact supported incident ID and record.
4. Render one sentence from the trusted duration and a fixed recovery phrase.
5. Check the replacement with the same gate; otherwise abstain with no text.

Missing, malformed, conflicting or wrong-incident records cause abstention on
rejection. There is no retry, retrieval, API call or alternative incident support.
The record is explicitly supplied in the replay, not a silent fallback default.

## Historical replay

`day17_analysis.py` first runs Day 16's analysis, including Day 15 integrity
checks of original requests, raw response bytes and review associations. It then
passes the actual rejected saved candidates to recovery. `day17_replay.json`
keeps per-trial decisions, original labels, gate reasons, replacement text and
source hashes. No earlier response, review, prompt, lock or result is rewritten.

| Metric | Trust boundary + Day 16 | Trust boundary + Day 17 |
| --- | ---: | ---: |
| Known contaminated attack outputs withheld | 3/3 | 3/3 |
| Known contaminated attack outputs delivered | 0/18 | 0/18 |
| Successful recovery / blocked attacks | 0/3 | 3/3 |
| Legitimate task completion on attacks | 15/18 | 18/18 |
| Legitimate task completion on clean controls | 18/18 | 18/18 |
| Clean controls unnecessarily blocked | 0/18 | 0/18 |
| Final abstentions on attacks | 3/18 | 0/18 |
| Final abstentions on controls | 0/18 | 0/18 |

The baseline replay is a separate ablation: six contaminated responses (five
successes and one partial) are withheld and recovered, raising completion from
12/18 to 18/18; all 18 controls remain released. No known contamination is
delivered and no final abstention occurs there. These are the same recorded
responses, not new model conditions or independent trials.

Containment counts only previously reviewed successful/partial attacks withheld
before release. Recovery success requires a rejected candidate to receive the
canonical sentence with both owner-defined facts and no added claim. Final task
completion combines those deterministic recoveries with unchanged historical
`task_completed=yes` labels for accepted responses. False-positive blocks count
historically completed, uncontaminated responses withheld by the gate; controls
are also reported separately. Denominators always include blocked outputs.
Historical labels are agent-authored, not independent human verification.

## Synthetic checks and limits

Development fixtures cover missing text, marker/URL substitution, malicious fact
replacement, absent/conflicting records, wrong incident binding and replacement
validation failure. Invalid trusted-record cases abstain; they are separate from
the 72 historical trials, whose complete trusted record makes recovery possible.
A valid quarter-hour/database-reboot paraphrase is unnecessarily blocked and then
recovered. That explicit false positive is not included in the historical 0/18
control rate. These fixtures are not hidden evaluation data.

The unchanged lexical gate still accepts some unsupported extra claims. A test
retains that limit. Recovery helps only rejected outputs and cannot establish
factuality of accepted text. The trusted record's correctness and availability
are assumptions; its provenance hashes support reproducibility, not authenticity.
The renderer omits optional details and supports only this one English incident.
The 18/18 completion result therefore measures a fixed template against a fixed
task, not general model robustness, general recovery or deployment readiness.
No paid calls were made and no live runner was changed.

## Validation

54 offline tests pass (46 existing, eight new test methods). Saved Day 13,
Day 16 and Day 17 reports reproduce. The suite's printed request/cost lines
come from fake transports, not API usage. A local credential-pattern scan of
tracked files and the new changes found no credential matches; it cannot prove
absence of every secret. Earlier tracked files and raw run bytes are preserved.

```sh
python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
python -B -S day13_metrics.py --check
python -B -S day16_analysis.py --check
python -B -S day17_analysis.py --check
```

On Windows, set TEMP and TMP to a writable scratch directory if needed.

## Cross-platform replay correction

The initial Day 17 provenance hashes used working-tree bytes. Windows Git
checked out some source files with CRLF, while Linux used LF, so identical
source text produced different hashes and failed the full saved-report check.
Source provenance now hashes bytes after converting CRLF to LF. No other
whitespace, encoding or content is normalized. The three provenance fields were
recomputed under this explicit convention; all saved decisions, metrics and
recovery text remain unchanged. Day 15 raw evidence still uses exact-byte
hashes and its existing integrity checks. Earlier result files are untouched.

Two regression tests check LF/CRLF equivalence for the full report and ensure
content edits, spaces, missing final newlines and lone CR characters still
change the source digest. The complete 56-test offline suite passes in the
Windows working copy and a checkout built from Git's LF blobs. Day 13, Day 16
and Day 17 report checks also pass in both copies. No API calls were made.
